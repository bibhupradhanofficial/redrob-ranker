import os
import json
import gzip
import logging
import re
from typing import Iterator, List, Dict, Optional
from tqdm import tqdm

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, filepath: str):
        # Accepts .jsonl or .jsonl.gz paths
        self.filepath = filepath

    def stream_candidates(self) -> Iterator[dict]:
        # Yields one candidate dict at a time
        # Uses gzip.open for .gz files, open() for .jsonl
        # Skips malformed lines with a warning (don't crash)
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        is_gz = self.filepath.endswith('.gz')
        open_func = gzip.open if is_gz else open
        mode = 'rt' if is_gz else 'r'
        encoding = 'utf-8'

        # Check if the file starts with '[' (signaling a JSON array)
        first_char = ""
        try:
            with open_func(self.filepath, mode, encoding=encoding) as f:
                # Read a small chunk to find the first non-whitespace character
                chunk = f.read(100)
                for char in chunk:
                    if char.strip():
                        first_char = char
                        break
        except Exception:
            pass

        # If it looks like a JSON array, parse the whole array (safe for smaller files like sample_candidates.json)
        if first_char == '[':
            try:
                with open_func(self.filepath, mode, encoding=encoding) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                yield item
                            else:
                                logger.warning("Skipping non-dict item in JSON array")
                        return
            except json.JSONDecodeError:
                # If JSON parsing fails, fall back to line-by-line parsing
                pass

        # Standard line-by-line JSONL parser
        with open_func(self.filepath, mode, encoding=encoding) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping malformed line {line_num} in {self.filepath}: {e}")

    def load_all(self, max_candidates: Optional[int] = None) -> List[dict]:
        # Loads all (or up to max_candidates) into a list
        # Shows a tqdm progress bar with "Loading candidates..."
        candidates = []
        generator = self.stream_candidates()
        
        pbar = tqdm(desc="Loading candidates...", total=max_candidates, unit="cand")
        try:
            for c in generator:
                candidates.append(c)
                pbar.update(1)
                if max_candidates is not None and len(candidates) >= max_candidates:
                    break
        finally:
            pbar.close()
            
        return candidates

    def load_batch(self, batch_size: int = 1000) -> Iterator[List[dict]]:
        # Yields lists of batch_size candidates at a time
        batch = []
        for c in self.stream_candidates():
            batch.append(c)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    @staticmethod
    def get_candidate_text(c: dict) -> str:
        # Concatenates: headline + summary + all career description texts +
        #               all skill names + current_title
        # Used for TF-IDF and semantic scoring
        # Returns a single clean string (strip whitespace, lowercase)
        parts = []
        profile = c.get("profile") or {}

        # 1. Headline
        headline = profile.get("headline") or c.get("headline") or ""
        if headline:
            parts.append(str(headline))

        # 2. Summary
        summary = profile.get("summary") or c.get("summary") or ""
        if summary:
            parts.append(str(summary))

        # 3. All career description texts
        history = c.get("career_history") or []
        if isinstance(history, list):
            for entry in history:
                if isinstance(entry, dict):
                    desc = entry.get("description") or entry.get("job_description") or ""
                    if desc:
                        parts.append(str(desc))

        # 4. All skill names
        skills = c.get("skills") or []
        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    skill_name = skill.get("name") or skill.get("skill_name") or ""
                else:
                    skill_name = skill
                if skill_name:
                    parts.append(str(skill_name))
        elif isinstance(skills, str) and skills:
            parts.append(skills)

        # 5. Current title
        current_title = (
            profile.get("current_title")
            or c.get("current_title")
            or profile.get("title")
            or c.get("title")
            or ""
        )
        if current_title:
            parts.append(str(current_title))

        # Clean, lowercase, and collapse whitespace
        full_text = " ".join(parts).lower()
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        return full_text

    @staticmethod
    def get_career_companies(c: dict) -> List[str]:
        # Returns list of all company names from career_history
        history = c.get("career_history") or []
        companies = []
        if isinstance(history, list):
            for entry in history:
                if isinstance(entry, dict):
                    name = entry.get("company_name") or entry.get("company") or entry.get("companyName")
                    if name:
                        companies.append(str(name).strip())
        return companies

    @staticmethod
    def get_career_titles(c: dict) -> List[str]:
        # Returns list of all titles from career_history
        history = c.get("career_history") or []
        titles = []
        if isinstance(history, list):
            for entry in history:
                if isinstance(entry, dict):
                    title = entry.get("title") or entry.get("job_title") or entry.get("jobTitle")
                    if title:
                        titles.append(str(title).strip())
        return titles

    @staticmethod
    def get_career_industries(c: dict) -> List[str]:
        # Returns list of all industries from career_history
        history = c.get("career_history") or []
        industries = []
        if isinstance(history, list):
            for entry in history:
                if isinstance(entry, dict):
                    industry = entry.get("industry") or entry.get("company_industry")
                    if industry:
                        if isinstance(industry, list):
                            industries.extend([str(ind).strip() for ind in industry if ind])
                        else:
                            industries.append(str(industry).strip())
        return industries
