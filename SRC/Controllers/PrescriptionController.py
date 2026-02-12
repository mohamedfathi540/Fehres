"""
PrescriptionController — OCR prescription images, extract medicine names,
and search for active ingredients + images.
"""
import os
import re
import json
import logging
import tempfile
from typing import List, Optional

from .BaseController import basecontroller
from Helpers.Config import get_settings

logger = logging.getLogger("uvicorn.error")


class PrescriptionController(basecontroller):

    def __init__(self):
        super().__init__()
        self.settings = get_settings()

    # -----------------------------------------------------------------
    # 1. OCR the prescription image using LlamaParse
    # -----------------------------------------------------------------
    async def ocr_prescription(self, file_path: str) -> str:
        """
        Use LlamaParse to OCR an image file and return the extracted text.
        Supports jpg, jpeg, png, webp, and pdf.
        """
        from llama_parse import LlamaParse

        api_key = self.settings.LLAMA_CLOUD_API_KEY
        if not api_key:
            raise ValueError("LLAMA_CLOUD_API_KEY is not set in .env")

        parser = LlamaParse(
            api_key=api_key,
            result_type="text",
            parsing_instruction=(
                "This is a medical prescription from a doctor. "
                "Extract ALL text exactly as written, especially medicine names, "
                "dosages, and instructions. Preserve the original language."
            ),
        )

        documents = await parser.aload_data(file_path)

        if not documents:
            return ""

        # Combine all pages into a single text
        full_text = "\n".join(doc.text for doc in documents)
        logger.info("LlamaParse OCR extracted %d characters", len(full_text))
        return full_text

    # -----------------------------------------------------------------
    # 2. Extract medicine names from OCR text (using LLM or regex)
    # -----------------------------------------------------------------
    async def extract_medicine_names(self, ocr_text: str, genration_client) -> List[str]:
        """
        Use the LLM generation client to extract ONLY medicine names
        from the OCR text, ignoring doctor names, clinic addresses,
        dates, dosage instructions, etc.
        Returns a list of medicine name strings.
        """
        from fastapi.concurrency import run_in_threadpool

        if not ocr_text or not ocr_text.strip():
            return []

        prompt = (
            "You are a medical prescription parser. "
            "Given the following text extracted from a doctor's prescription via OCR, "
            "extract ONLY the medicine/drug names. "
            "IGNORE the following: doctor name, clinic name, clinic address, phone numbers, "
            "dates, patient name, dosage instructions (like '3 times a day'), quantities, "
            "and any other non-medicine text.\n\n"
            "Return the result as a JSON array of strings, each being a medicine name. "
            "If you find no medicines, return an empty array [].\n"
            "Return ONLY the JSON array, no explanation.\n\n"
            f"--- Prescription Text ---\n{ocr_text}\n--- End ---"
        )

        try:
            # Run synchronous generation in threadpool to avoid blocking event loop
            response = await run_in_threadpool(
                genration_client.genrate_text,
                prompt=prompt,
                chat_history=[],
                max_output_tokens=1024,
                temperature=0.1,
            )

            if not response:
                logger.warning("LLM returned empty response for medicine extraction")
                return []

            # Clean the response — strip markdown code fences if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                # Remove opening and closing fences
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

            medicines = json.loads(cleaned)
            if isinstance(medicines, list):
                # Filter out empty strings
                return [m.strip() for m in medicines if isinstance(m, str) and m.strip()]
            return []

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON: %s", e)
            logger.error("Raw response: %s", response if 'response' in dir() and response else "N/A")
            return []
        except Exception as e:
            logger.error("Error during medicine name extraction: %s", e)
            return []

    # -----------------------------------------------------------------
    # 3. Search for medicine info (active ingredient + image)
    # -----------------------------------------------------------------
    async def search_medicine_info(self, medicine_name: str) -> dict:
        """
        Use DuckDuckGo to find:
        - The active ingredient of the medicine
        - An image/picture of the medicine
        Returns a dict: {name, active_ingredient, image_url}
        """
        from duckduckgo_search import DDGS

        result = {
            "name": medicine_name,
            "active_ingredient": "",
            "image_url": None,
        }

        try:
            ddgs = DDGS()

            # --- Search for active ingredient ---
            text_query = f"{medicine_name} active ingredient"
            text_results = ddgs.text(text_query, max_results=3)

            if text_results:
                # Combine top results and try to extract the active ingredient
                snippets = " ".join(
                    r.get("body", "") for r in text_results
                )
                # The active ingredient is usually mentioned directly
                result["active_ingredient"] = self._extract_active_ingredient(
                    medicine_name, snippets
                )

            # --- Search for medicine image ---
            image_query = f"{medicine_name} medicine pill box"
            image_results = ddgs.images(image_query, max_results=3)

            if image_results:
                # Take the first image result
                result["image_url"] = image_results[0].get("image", None)

        except Exception as e:
            logger.error("Error searching for medicine '%s': %s", medicine_name, e)

        return result

    def _extract_active_ingredient(self, medicine_name: str, snippets: str) -> str:
        """
        Try to extract the active ingredient from search snippets.
        Falls back to returning the most relevant snippet sentence.
        """
        if not snippets:
            return "Not found"

        # Look for common patterns like "contains <ingredient>"
        # or "<medicine> (active ingredient: <X>)"
        patterns = [
            r"active\s+ingredient[s]?\s*(?:is|are|:)\s*([^.;,]+)",
            r"contains?\s+(?:the\s+)?active\s+(?:ingredient|substance)\s*[:.]?\s*([^.;,]+)",
            r"generic\s+name\s*[:.]?\s*([^.;,]+)",
            r"(?:active\s+)?(?:ingredient|substance|component)\s*[:.]?\s*([^.;,]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, snippets, re.IGNORECASE)
            if match:
                ingredient = match.group(1).strip()
                # Clean up trailing words that are not part of the ingredient
                ingredient = re.split(r"\b(?:which|that|and is|it is|this)\b", ingredient, flags=re.IGNORECASE)[0].strip()
                if ingredient and len(ingredient) < 200:
                    return ingredient

        # Fallback: return first 150 chars of snippets as context
        return snippets[:150].strip() + "..."

    # -----------------------------------------------------------------
    # Full pipeline: OCR → Extract → Search
    # -----------------------------------------------------------------
    async def analyze_prescription(
        self, file_path: str, genration_client
    ) -> dict:
        """
        Full pipeline:
        1. OCR the prescription image
        2. Extract medicine names via LLM
        3. Search for each medicine's active ingredient + image
        Returns {ocr_text, medicines: [{name, active_ingredient, image_url}]}
        """
        # Step 1: OCR
        ocr_text = await self.ocr_prescription(file_path)

        if not ocr_text.strip():
            return {
                "ocr_text": "",
                "medicines": [],
            }

        # Step 2: Extract medicine names
        medicine_names = await self.extract_medicine_names(
            ocr_text, genration_client
        )

        if not medicine_names:
            return {
                "ocr_text": ocr_text,
                "medicines": [],
            }

        # Step 3: Search for each medicine
        medicines = []
        for name in medicine_names:
            info = await self.search_medicine_info(name)
            medicines.append(info)

        return {
            "ocr_text": ocr_text,
            "medicines": medicines,
        }
