import csv
import os
import logging
import re
from typing import List, Optional, Tuple, Dict
from thefuzz import process, fuzz

logger = logging.getLogger("uvicorn.error")

class MedicineMatcher:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MedicineMatcher, cls).__new__(cls)
            cls._instance.medicines = []
            cls._instance.medicine_map = {}
            cls._instance.ingredient_map = {} # brand.lower() -> ingredient
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._load_data()
        self._initialized = True

    def _load_data(self):
        """Load medicines from CSVs and fallback list."""
        
        # 1. Load from Primary CSV (Pharmacy_Products.csv)
        # Using relative path assuming this file is in SRC/Utils
        csv_path = os.path.join(
            os.path.dirname(__file__), 
            "../Assets/Files/1/Pharmacy_Products.csv"
        )
        csv_path = os.path.abspath(csv_path)

        count = 0
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get("name")
                        if name:
                            name = name.strip()
                            if name.lower() not in self.medicine_map:
                                self.medicines.append(name)
                                self.medicine_map[name.lower()] = name
                                count += 1
                            
                            # Add first word as candidate for better matching
                            first_word = name.split()[0]
                            clean_first = "".join(filter(str.isalnum, first_word))
                            if len(clean_first) > 3 and clean_first.lower() not in self.medicine_map:
                                self.medicines.append(clean_first)
                                self.medicine_map[clean_first.lower()] = name # Map back to full name
                logger.info(f"Loaded {count} medicines from Pharmacy_Products.csv")
            except Exception as e:
                logger.error(f"Failed to load {csv_path}: {e}")
        else:
            logger.warning(f"Pharmacy_Products.csv not found at {csv_path}")

        # 2. Load from Scraped CSV (eda_medicines.csv) if exists
        eda_path = os.path.join(
            os.path.dirname(__file__),
            "../Assets/Files/eda_medicines.csv"
        )
        eda_path = os.path.abspath(eda_path)

        if os.path.exists(eda_path):
            try:
                eda_count = 0
                with open(eda_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Assumes 'Trade Name' or 'name' column
                        name = row.get("Trade Name") or row.get("name")
                        if name:
                            name = name.strip()
                            if name.lower() not in self.medicine_map:
                                self.medicines.append(name)
                                self.medicine_map[name.lower()] = name
                                eda_count += 1
                logger.info(f"Loaded {eda_count} medicines from eda_medicines.csv")
            except Exception as e:
                logger.error(f"Failed to load {eda_path}: {e}")

        # 3. Fallback List (Hardcoded commonly used)
        fallback_list = [
            "Augmentin", "Moxclav", "Megamox", "Hibiotic",
            "Phenadon", "Phinex", "Rhinex",
            "Cataflam", "Voltaren",
            "Antinal",
            "Kongestal", "Comtrex",
            "Panadol", "Brufen",
            "Flagyl", "Amrizole",
            "Nexium", "Omeprazole",
            "Ciprocin", "Xithrone",
            "Glucophage", "Concor",
            "Ventolin",
            "Amaryl", "Symbicort", "Prednisolone", "Aspocid"
        ]
        
        fallback_count = 0
        for name in fallback_list:
            if name.lower() not in self.medicine_map:
                self.medicines.append(name)
                self.medicine_map[name.lower()] = name
                fallback_count += 1
        
        logger.info(f"MedicineMatcher initialized with {len(self.medicines)} total unique medicines.")

    def get_active_ingredient(self, name: str) -> Optional[str]:
        """Get the active ingredient for a known brand name."""
        return self.ingredient_map.get(name.lower())

    def register_ingredient(self, brand: str, ingredient: str):
        """Map a brand name to an active ingredient."""
        brand_lower = brand.lower()
        self.ingredient_map[brand_lower] = ingredient
        
        # Also map the canonical name from the CSV if we have one for this brand
        # This ensures that if "Augmentin" -> "Augmentin 875mg...", the full name also gets the ingredient
        canonical = self.medicine_map.get(brand_lower)
        if canonical:
            self.ingredient_map[canonical.lower()] = ingredient
        
    def find_best_match(self, query: str, threshold: int = 85) -> Optional[str]:
        """
        Find the best fuzzy match for the query.
        Returns the matched name if detection confidence >= threshold, else None.
        """
        if not query or len(query) < 3:
            return None
            
        q_lower = query.lower()
        if q_lower in self.medicine_map:
            return self.medicine_map[q_lower]
            
        # Extract matches
        # extractOne returns (match, score, index) or just (match, score) depending on version
        # process.extractOne("query", choices)
        
        try:
            # WRatio handles partial matches and case differences better than token_sort_ratio
            result = process.extractOne(query, self.medicines, scorer=fuzz.WRatio)
            
            if result:
                # result is expected to be a tuple (match_string, score, index)
                # handle cases where it might be just (match, score)
                if len(result) >= 2:
                    match_name = result[0]
                    score = result[1]
                    
                    if score >= threshold:
                        logger.info(f"Fuzzy Match: '{query}' -> '{match_name}' (Score: {score})")
                        # Return the mapped full name to ensure canonical result
                        return self.medicine_map.get(match_name.lower(), match_name)
        except Exception as e:
            logger.error(f"Fuzzy match error for '{query}': {e}")
        
        return None
    def find_medicines_by_ingredient(self, ingredient: str, limit: int = 5) -> List[str]:
        """
        Search the database for medicines containing the given active ingredient.
        """
        if not ingredient or ingredient.lower() == "unknown":
            return []
            
        ingredient_lower = ingredient.lower()
        # Split complex ingredients like "Amoxicillin + Clavulanic acid"
        parts = [p.strip() for p in re.split(r'[+&/|,]', ingredient_lower) if len(p.strip()) > 3]
        
        matches = []
        seen = set()
        
        # Simple heuristic: for each part of the ingredient, look for it in medicine names
        for med_name in self.medicines:
            med_lower = med_name.lower()
            
            # Avoid matching the exact same brand if possible (though we'll filter later)
            # If all parts are found in the name, it's likely a match
            matches_all = True
            for part in parts:
                if part not in med_lower:
                    matches_all = False
                    break
            
            if matches_all and med_name not in seen:
                # Get the full canonical name
                canonical = self.medicine_map.get(med_lower, med_name)
                if canonical not in seen:
                    matches.append(canonical)
                    seen.add(canonical)
                if len(matches) >= limit:
                    break
        
        return matches

