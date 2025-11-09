import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()


def parse_markdown_json(content: str) -> dict:
    """
    마크다운 형태의 JSON 응답을 파싱하는 함수.
    OpenAI가 ```json ... ``` 또는 ``` ... ``` 형태로 응답하는 경우를 처리.
    
    Args:
        content: OpenAI 응답 문자열 (마크다운 JSON 포함 가능)
    
    Returns:
        파싱된 JSON 딕셔너리
    """
    # 먼저 일반 JSON 파싱 시도
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 마크다운 코드 블록 제거 시도 (```json ... ``` 또는 ``` ... ```)
    patterns = [
        r'```json\s*(.*?)\s*```',  # ```json ... ```
        r'```\s*(.*?)\s*```',       # ``` ... ```
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
    
    # 코드 블록이 없으면 전체 내용에서 JSON 부분 추출 시도
    # { 로 시작하고 } 로 끝나는 부분 찾기
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # 마지막 시도: 앞뒤 공백 제거 후 다시 시도
    content_stripped = content.strip()
    try:
        return json.loads(content_stripped)
    except json.JSONDecodeError:
        raise ValueError(f"JSON 파싱 실패. 원본 내용:\n{content[:500]}")


class Reviewer:
    def __init__(self, model: str = "gpt-4o-mini", prompts_dir: str = "./prompts/paper_review"):

        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.reviews = []

        prompts_path = Path(prompts_dir)
        self.reviewer_system = (prompts_path / "reviewer_system.txt").read_text(encoding="utf-8")
        self.paper_review = (prompts_path / "paper_review.txt").read_text(encoding="utf-8")
        self.neurips_reviewer_guidelines = (prompts_path / "neurips_reviewer_guidelines.txt").read_text(encoding="utf-8")
        self.few_shot_review_examples = (prompts_path / "few_shot_review_examples.txt").read_text(encoding="utf-8")
        self.paper_reflection = (prompts_path / "paper_reflection.txt").read_text(encoding="utf-8")
        self.ensemble_system = (prompts_path / "ensemble_system.txt").read_text(encoding="utf-8")

    async def review(self, paper_content: str, reflection: int = 3) -> list[dict]:
        """
        논문을 리뷰하는 메인 함수
        
        Args:
            paper_content: 논문 텍스트 내용
            reflection: 리플렉션 라운드 수 (기본값: 3)
        
        Returns:
            리뷰 딕셔너리 리스트
        """
        messages = [{'role': 'system', 'content': self.reviewer_system}]

        paper_review = self.paper_review 

        paper_review = paper_review.replace("{neurips_reviewer_guidelines}", self.neurips_reviewer_guidelines)
        paper_review = paper_review.replace("{few_show_examples}", self.few_shot_review_examples)
        paper_review = paper_review.replace("{paper}", paper_content)

        prompt = paper_review

        messages.append({'role': 'user', 'content': prompt})

        # 1) 최초 리뷰 생성
        print("==> initial review generation start...")
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        print(completion.choices[0].message.content)

        try:
            review_json = parse_markdown_json(completion.choices[0].message.content)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"review JSON parsing failed: {e}")
            return []

        self.reviews.append(review_json)
        messages.append({'role': 'assistant', 'content': completion.choices[0].message.content})
        print("==> initial review generation done.")

        # 2) 리뷰 리플렉션 생성
        for i in range(reflection):
            round_num = i + 1
            print(f"==> reflection {round_num}/{reflection} start...")
            messages.append({'role': 'user', 'content': f"Round {round_num}/{reflection}." + self.paper_reflection})

            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            try:
                reflection_json = parse_markdown_json(completion.choices[0].message.content)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"reflection {round_num} JSON parsing failed: {e}")
                return self.reviews

            self.reviews.append(reflection_json)
            messages.append({'role': 'assistant', 'content': completion.choices[0].message.content})
            print(f"==> reflection {round_num}/{reflection} done.")

            if 'i am done' in completion.choices[0].message.content.lower():
                print("reflection early done")
                break

        return self.reviews

    async def review_ensembling(self) -> list[dict]:
        """
        여러 리뷰를 앙상블하여 최종 리뷰 생성
        
        Returns:
            앙상블된 최종 리뷰 딕셔너리 리스트
        """
        if not self.reviews:
            raise ValueError("No reviews available for ensembling.")

        print("==> review ensembling start...")
        
        self.ensemble_system = self.ensemble_system.replace("{reviewer_count}", str(len(self.reviews)))

        messages = [{'role': 'system', 'content': self.ensemble_system}]

        prompt = ""
        for idx, content in enumerate(self.reviews):
            review_text = json.dumps(content, indent=2) if isinstance(content, dict) else str(content)
            prompt += f"Review {idx + 1}/{len(self.reviews)}:\n{review_text}\n\n"

        prompt += "\n\n\n\n\n" + self.neurips_reviewer_guidelines
        messages.append({'role': 'user', 'content': prompt})

        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        try:
            final_review = parse_markdown_json(completion.choices[0].message.content)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ensembling review JSON parsing failed: {e}")
            return self.reviews

        self.reviews = [final_review]
        print("==> review ensembling done.")

        return self.reviews

    def is_review_strong_enough(self, score_threshold: float = 3.0, confidence_threshold: float = 3.0) -> bool:
        """
        리뷰가 충분히 강한지 확인
        
        Args:
            score_threshold: 최소 점수 임계값
            confidence_threshold: 최소 신뢰도 임계값
        
        Returns:
            리뷰가 충분히 강하면 True
        """
        for review in self.reviews:
            if isinstance(review, dict):
                overall = review.get("overall_score")
                confidence = review.get("confidence")
                try:
                    if overall is not None and confidence is not None:
                        if float(overall) >= score_threshold and float(confidence) >= confidence_threshold:
                            return True
                except ValueError:
                    continue
        return False

