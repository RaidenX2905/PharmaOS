import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import re
from difflib import SequenceMatcher


class DrugInteractionChecker:
    def __init__(self):
        self.interaction_cache = {}
        self.substitution_cache = {}

        # Common drug interaction patterns and severities
        self.known_interactions = {
            # Format: (drug1, drug2): {'severity', 'description', 'clinical_effect', 'management'}
            ("aspirin", "warfarin"): {
                "severity": "Severe",
                "description": "Increased risk of bleeding",
                "clinical_effect": "Enhanced anticoagulant effect",
                "management": "Monitor INR closely, consider dose adjustment",
            },
            ("metformin", "contrast media"): {
                "severity": "Moderate",
                "description": "Risk of lactic acidosis",
                "clinical_effect": "Potential kidney dysfunction",
                "management": "Hold metformin 48 hours post-contrast",
            },
            ("digoxin", "furosemide"): {
                "severity": "Moderate",
                "description": "Increased digoxin toxicity risk",
                "clinical_effect": "Hypokalemia enhances digoxin effect",
                "management": "Monitor potassium and digoxin levels",
            },
        }

        # Drug categories for interaction checking
        self.drug_categories = {
            "anticoagulants": ["warfarin", "heparin", "aspirin", "clopidogrel"],
            "antidiabetics": ["metformin", "insulin", "glipizide", "glyburide"],
            "antibiotics": [
                "amoxicillin",
                "ciprofloxacin",
                "azithromycin",
                "doxycycline",
            ],
            "cardiovascular": ["atenolol", "lisinopril", "amlodipine", "digoxin"],
            "analgesics": ["paracetamol", "ibuprofen", "morphine", "tramadol"],
            "steroids": ["prednisolone", "hydrocortisone", "dexamethasone"],
        }

        # Drug substitution database
        self.substitutions = {
            "paracetamol": [
                {
                    "name": "Acetaminophen",
                    "generic_name": "Acetaminophen",
                    "strength": "500mg",
                    "dosage_form": "Tablet",
                    "manufacturer": "Various",
                    "similarity": 1.0,
                    "notes": "Same active ingredient, different brand name",
                },
                {
                    "name": "Ibuprofen",
                    "generic_name": "Ibuprofen",
                    "strength": "400mg",
                    "dosage_form": "Tablet",
                    "manufacturer": "Various",
                    "similarity": 0.8,
                    "notes": "Alternative NSAID, different mechanism",
                },
            ],
            "amoxicillin": [
                {
                    "name": "Ampicillin",
                    "generic_name": "Ampicillin",
                    "strength": "250mg",
                    "dosage_form": "Capsule",
                    "manufacturer": "Various",
                    "similarity": 0.9,
                    "notes": "Similar penicillin antibiotic",
                },
                {
                    "name": "Azithromycin",
                    "generic_name": "Azithromycin",
                    "strength": "250mg",
                    "dosage_form": "Tablet",
                    "manufacturer": "Various",
                    "similarity": 0.7,
                    "notes": "Alternative antibiotic, different class",
                },
            ],
            "metformin": [
                {
                    "name": "Glipizide",
                    "generic_name": "Glipizide",
                    "strength": "5mg",
                    "dosage_form": "Tablet",
                    "manufacturer": "Various",
                    "similarity": 0.6,
                    "notes": "Alternative diabetes medication, different mechanism",
                },
                {
                    "name": "Insulin Glargine",
                    "generic_name": "Insulin Glargine",
                    "strength": "100 units/mL",
                    "dosage_form": "Injection",
                    "manufacturer": "Various",
                    "similarity": 0.5,
                    "notes": "Alternative for severe cases, different administration",
                },
            ],
        }

    def normalize_drug_name(self, drug_name: str) -> str:
        """Normalize drug name for consistent matching"""
        if not drug_name:
            return ""

        # Remove common suffixes and dosages
        normalized = re.sub(r"\s*\d+\s*mg.*$", "", drug_name, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*\d+\s*mcg.*$", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*tablet.*$", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*capsule.*$", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*injection.*$", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*inhaler.*$", "", normalized, flags=re.IGNORECASE)

        return normalized.strip().lower()

    def check_interactions(self, drug_list: List[str]) -> List[Dict]:
        """Check for drug interactions in a list of drugs"""
        if len(drug_list) < 2:
            return []

        interactions = []
        normalized_drugs = [self.normalize_drug_name(drug) for drug in drug_list]

        # Check each pair of drugs
        for i in range(len(drug_list)):
            for j in range(i + 1, len(drug_list)):
                drug1 = normalized_drugs[i]
                drug2 = normalized_drugs[j]
                original_drug1 = drug_list[i]
                original_drug2 = drug_list[j]

                # Check direct interactions
                interaction = self.get_direct_interaction(drug1, drug2)
                if interaction:
                    interactions.append(
                        {
                            "drug1": original_drug1,
                            "drug2": original_drug2,
                            "severity": interaction["severity"],
                            "description": interaction["description"],
                            "clinical_effect": interaction["clinical_effect"],
                            "management": interaction["management"],
                            "alternatives": self.get_alternatives_for_interaction(
                                drug1, drug2
                            ),
                        }
                    )

                # Check category-based interactions
                category_interaction = self.check_category_interaction(drug1, drug2)
                if category_interaction:
                    interactions.append(
                        {
                            "drug1": original_drug1,
                            "drug2": original_drug2,
                            "severity": category_interaction["severity"],
                            "description": category_interaction["description"],
                            "clinical_effect": category_interaction["clinical_effect"],
                            "management": category_interaction["management"],
                            "alternatives": [],
                        }
                    )

        return interactions

    def get_direct_interaction(self, drug1: str, drug2: str) -> Optional[Dict]:
        """Get direct interaction between two drugs"""
        # Check both orders
        interaction_key1 = (drug1, drug2)
        interaction_key2 = (drug2, drug1)

        if interaction_key1 in self.known_interactions:
            return self.known_interactions[interaction_key1]
        elif interaction_key2 in self.known_interactions:
            return self.known_interactions[interaction_key2]

        # Check partial matches
        for (known_drug1, known_drug2), interaction in self.known_interactions.items():
            if (drug1 in known_drug1 or known_drug1 in drug1) and (
                drug2 in known_drug2 or known_drug2 in drug2
            ):
                return interaction
            elif (drug1 in known_drug2 or known_drug2 in drug1) and (
                drug2 in known_drug1 or known_drug1 in drug2
            ):
                return interaction

        return None

    def check_category_interaction(self, drug1: str, drug2: str) -> Optional[Dict]:
        """Check for interactions based on drug categories"""
        drug1_categories = self.get_drug_categories(drug1)
        drug2_categories = self.get_drug_categories(drug2)

        # Define category-based interaction rules
        risky_combinations = {
            ("anticoagulants", "anticoagulants"): {
                "severity": "Severe",
                "description": "Multiple anticoagulants increase bleeding risk",
                "clinical_effect": "Additive anticoagulant effects",
                "management": "Avoid combination, monitor INR/PT closely if unavoidable",
            },
            ("anticoagulants", "analgesics"): {
                "severity": "Moderate",
                "description": "NSAIDs may increase bleeding risk",
                "clinical_effect": "Enhanced anticoagulation",
                "management": "Use with caution, consider gastroprotection",
            },
            ("antibiotics", "anticoagulants"): {
                "severity": "Moderate",
                "description": "Some antibiotics may enhance warfarin effect",
                "clinical_effect": "Possible increased INR",
                "management": "Monitor INR more frequently",
            },
        }

        for cat1 in drug1_categories:
            for cat2 in drug2_categories:
                if (cat1, cat2) in risky_combinations:
                    return risky_combinations[(cat1, cat2)]
                elif (cat2, cat1) in risky_combinations:
                    return risky_combinations[(cat2, cat1)]

        return None

    def get_drug_categories(self, drug_name: str) -> List[str]:
        """Get categories for a drug"""
        categories = []
        for category, drugs in self.drug_categories.items():
            for known_drug in drugs:
                if drug_name in known_drug or known_drug in drug_name:
                    categories.append(category)
                    break
        return categories

    def get_alternatives_for_interaction(self, drug1: str, drug2: str) -> List[str]:
        """Get alternative drugs to avoid interaction"""
        alternatives = []

        # Find alternatives for drug1
        drug1_alternatives = self.find_substitutes(drug1, "Drug interaction")
        for alt in drug1_alternatives[:2]:  # Limit to 2 alternatives
            alternatives.append(f"Consider {alt['name']} instead of first drug")

        # Find alternatives for drug2
        drug2_alternatives = self.find_substitutes(drug2, "Drug interaction")
        for alt in drug2_alternatives[:2]:  # Limit to 2 alternatives
            alternatives.append(f"Consider {alt['name']} instead of second drug")

        return alternatives

    def get_safe_combinations(self, drug_list: List[str]) -> List[Dict]:
        """Get safe drug combinations from the list"""
        safe_combinations = []
        normalized_drugs = [self.normalize_drug_name(drug) for drug in drug_list]

        for i in range(len(drug_list)):
            for j in range(i + 1, len(drug_list)):
                drug1 = normalized_drugs[i]
                drug2 = normalized_drugs[j]
                original_drug1 = drug_list[i]
                original_drug2 = drug_list[j]

                # Check if combination is safe (no interactions found)
                if not self.get_direct_interaction(
                    drug1, drug2
                ) and not self.check_category_interaction(drug1, drug2):
                    safe_combinations.append(
                        {
                            "drug1": original_drug1,
                            "drug2": original_drug2,
                            "note": "No significant interactions detected",
                        }
                    )

        return safe_combinations

    def find_substitutes(self, drug_name: str, reason: str = "") -> List[Dict]:
        """Find substitute drugs for a given drug"""
        normalized_drug = self.normalize_drug_name(drug_name)

        # Check direct substitutions
        if normalized_drug in self.substitutions:
            substitutes = self.substitutions[normalized_drug].copy()

            # Filter based on reason
            if reason == "Out of stock":
                # Prefer exact matches or high similarity
                substitutes = [s for s in substitutes if s["similarity"] >= 0.8]
            elif reason == "Drug interaction":
                # Prefer different drug classes
                substitutes = [s for s in substitutes if s["similarity"] < 0.9]
            elif reason == "Patient allergy":
                # Prefer completely different mechanisms
                substitutes = [s for s in substitutes if s["similarity"] < 0.7]
            elif reason == "Cost optimization":
                # All substitutes are valid, sorted by similarity
                pass

            return substitutes

        # If no direct match, try partial matching
        for known_drug, subs in self.substitutions.items():
            similarity = SequenceMatcher(None, normalized_drug, known_drug).ratio()
            if similarity > 0.7:  # 70% similarity threshold
                return subs

        # Generate generic substitutes based on drug category
        return self.generate_generic_substitutes(normalized_drug, reason)

    def generate_generic_substitutes(self, drug_name: str, reason: str) -> List[Dict]:
        """Generate generic substitute suggestions"""
        categories = self.get_drug_categories(drug_name)
        substitutes = []

        for category in categories:
            if category in self.drug_categories:
                for alternative_drug in self.drug_categories[category]:
                    if alternative_drug != drug_name:
                        substitutes.append(
                            {
                                "name": alternative_drug.title(),
                                "generic_name": alternative_drug.title(),
                                "strength": "Various",
                                "dosage_form": "Various",
                                "manufacturer": "Various",
                                "similarity": 0.6,
                                "notes": f"Alternative {category} medication",
                            }
                        )

        # Limit to top 3 suggestions
        return substitutes[:3]

    def validate_prescription(self, prescription_drugs: List[str]) -> Dict:
        """Validate a prescription for drug interactions and safety"""
        validation_result = {
            "safe": True,
            "warnings": [],
            "critical_interactions": [],
            "recommendations": [],
        }

        # Check for interactions
        interactions = self.check_interactions(prescription_drugs)

        for interaction in interactions:
            if interaction["severity"].lower() == "severe":
                validation_result["safe"] = False
                validation_result["critical_interactions"].append(interaction)
            else:
                validation_result["warnings"].append(interaction)

        # Generate recommendations
        if not validation_result["safe"]:
            validation_result["recommendations"].append(
                "Review prescription due to severe drug interactions"
            )

        if validation_result["warnings"]:
            validation_result["recommendations"].append(
                "Monitor patient closely due to potential drug interactions"
            )

        if validation_result["safe"] and not validation_result["warnings"]:
            validation_result["recommendations"].append(
                "Prescription appears safe with no significant interactions detected"
            )

        return validation_result

    def get_interaction_summary(self, drug_list: List[str]) -> Dict:
        """Get a summary of all interactions for a drug list"""
        interactions = self.check_interactions(drug_list)

        summary = {
            "total_interactions": len(interactions),
            "severe_count": len(
                [i for i in interactions if i["severity"].lower() == "severe"]
            ),
            "moderate_count": len(
                [i for i in interactions if i["severity"].lower() == "moderate"]
            ),
            "mild_count": len(
                [i for i in interactions if i["severity"].lower() == "mild"]
            ),
            "risk_level": "Low",
        }

        # Determine overall risk level
        if summary["severe_count"] > 0:
            summary["risk_level"] = "High"
        elif summary["moderate_count"] > 2:
            summary["risk_level"] = "High"
        elif summary["moderate_count"] > 0 or summary["mild_count"] > 2:
            summary["risk_level"] = "Medium"

        return summary

    def add_custom_interaction(
        self,
        drug1: str,
        drug2: str,
        severity: str,
        description: str,
        clinical_effect: str,
        management: str,
    ):
        """Add a custom drug interaction to the knowledge base"""
        drug1_norm = self.normalize_drug_name(drug1)
        drug2_norm = self.normalize_drug_name(drug2)

        interaction_data = {
            "severity": severity,
            "description": description,
            "clinical_effect": clinical_effect,
            "management": management,
        }

        self.known_interactions[(drug1_norm, drug2_norm)] = interaction_data

        # Clear cache to ensure new interaction is used
        self.interaction_cache.clear()

    def get_drug_contraindications(self, drug_name: str) -> List[str]:
        """Get contraindications for a specific drug"""
        normalized_drug = self.normalize_drug_name(drug_name)

        # Common contraindications database
        contraindications = {
            "aspirin": [
                "Active bleeding",
                "Severe liver disease",
                "Children under 16 with viral infections",
                "Known aspirin allergy",
            ],
            "metformin": [
                "Severe kidney disease (eGFR < 30)",
                "Acute heart failure",
                "Severe liver disease",
                "Alcoholism",
            ],
            "warfarin": [
                "Active bleeding",
                "Pregnancy",
                "Severe liver disease",
                "Recent major surgery",
            ],
            "insulin": ["Hypoglycemia", "Known insulin allergy"],
        }

        # Check for exact or partial matches
        for known_drug, contras in contraindications.items():
            if normalized_drug in known_drug or known_drug in normalized_drug:
                return contras

        return []

    def check_dosage_compatibility(self, drug_combinations: List[Dict]) -> List[Dict]:
        """Check if drug dosages are compatible when used together"""
        compatibility_issues = []

        # This would typically involve complex pharmacokinetic calculations
        # For now, providing basic compatibility checks

        for combo in drug_combinations:
            drug1 = combo.get("drug1", "")
            drug2 = combo.get("drug2", "")

            # Example compatibility check
            if "warfarin" in drug1.lower() and "aspirin" in drug2.lower():
                compatibility_issues.append(
                    {
                        "drugs": [drug1, drug2],
                        "issue": "Dosage adjustment required",
                        "recommendation": "Reduce warfarin dose by 25-50% when used with aspirin",
                        "monitoring": "Monitor INR every 3-5 days initially",
                    }
                )

        return compatibility_issues
