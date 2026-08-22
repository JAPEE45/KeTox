"""
services/compound_lookup.py — Fast in-memory compound & SMILES resolver

Features:
- Loads curated data/cyp3a4_compounds.csv once on server startup.
- O(1) Instant local lookup using RDKit canonical SMILES.
- Bidirectional lookup: SMILES -> Compound Name & Details, and Compound Name -> SMILES.
- Zero network latency, completely offline.
"""

import os
import re
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdMolDescriptors
from typing import Optional, Dict, Any

# Suppress RDKit terminal error spam during parsing checks
RDLogger.DisableLog("rdApp.*")

# Locate CSV
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CSV_FILE_PATH = os.path.join(DATA_DIR, "cyp3a4_compounds.csv")

# In-memory dictionaries
CANONICAL_SMILES_INDEX: Dict[str, Dict[str, Any]] = {}
NAME_TO_SMILES_INDEX: Dict[str, str] = {}
_INITIALIZED = False


def _normalize_name_key(name: str) -> str:
    """Normalizes string for fuzzy name matching (lowercase, no punctuation/spaces)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def init_compound_library(force_reload: bool = False):
    """Loads CSV into in-memory hash maps for sub-millisecond lookups."""
    global CANONICAL_SMILES_INDEX, NAME_TO_SMILES_INDEX, _INITIALIZED
    
    if _INITIALIZED and not force_reload:
        return

    CANONICAL_SMILES_INDEX.clear()
    NAME_TO_SMILES_INDEX.clear()

    if not os.path.exists(CSV_FILE_PATH):
        # If not present, try running build script
        try:
            from data.build_cyp3a4_dataset import build_dataset
            build_dataset()
        except Exception as e:
            print(f"Warning: Could not build compound dataset: {e}")
            return

    if os.path.exists(CSV_FILE_PATH):
        try:
            df = pd.read_csv(CSV_FILE_PATH)
            for _, row in df.iterrows():
                canon = str(row.get("canonical_smiles", "")).strip()
                name = str(row.get("name", "")).strip()
                raw_smiles = str(row.get("smiles", "")).strip()
                formula = str(row.get("formula", "")).strip()
                cid = row.get("cid", "")
                activity = str(row.get("activity_class", "")).strip()

                if canon and name:
                    entry = {
                        "name": name,
                        "canonical_smiles": canon,
                        "smiles": raw_smiles or canon,
                        "formula": formula,
                        "cid": cid,
                        "activity_class": activity
                    }
                    CANONICAL_SMILES_INDEX[canon] = entry
                    
                    # Also map standard names and aliases
                    norm_name = _normalize_name_key(name)
                    NAME_TO_SMILES_INDEX[norm_name] = canon

                    # If name contains parentheses e.g. "Aspirin (Acetylsalicylic acid)", index both parts
                    if "(" in name and ")" in name:
                        part1 = re.sub(r"\(.*?\)", "", name).strip()
                        part2 = name[name.find("(") + 1 : name.find(")")].strip()
                        if part1:
                            NAME_TO_SMILES_INDEX[_normalize_name_key(part1)] = canon
                        if part2:
                            NAME_TO_SMILES_INDEX[_normalize_name_key(part2)] = canon

            _INITIALIZED = True
            print(f" Loaded {len(CANONICAL_SMILES_INDEX)} CYP3A4 compounds into memory cache.")
        except Exception as err:
            print(f"❌ Error loading {CSV_FILE_PATH}: {err}")


def lookup_by_smiles(smiles: str) -> Optional[Dict[str, Any]]:
    """
    Given any raw SMILES string:
    1. Standardizes it into canonical SMILES using RDKit.
    2. Returns the matched compound dictionary from the local dataset if found.
    """
    if not _INITIALIZED:
        init_compound_library()

    try:
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            return None
        canon = Chem.CanonSmiles(smiles.strip())
        return CANONICAL_SMILES_INDEX.get(canon)
    except Exception:
        return None


def lookup_by_name(name: str) -> Optional[str]:
    """
    Given a compound name (e.g., 'Aspirin', 'ketoconazole', 'midazolam'):
    Returns the canonical SMILES string if present in the local database.
    """
    if not _INITIALIZED:
        init_compound_library()

    norm = _normalize_name_key(name)
    return NAME_TO_SMILES_INDEX.get(norm)


def resolve_compound_input(query: str) -> Dict[str, Any]:
    """
    Universal resolver for user query:
    Handles both SMILES strings and chemical compound names.
    
    Returns a dictionary:
    {
        "is_valid": bool,
        "smiles": str or None,
        "canonical_smiles": str or None,
        "compound_name": str,
        "formula": str or None,
        "mol": Chem.Mol or None,
        "metadata": dict or None
    }
    """
    if not _INITIALIZED:
        init_compound_library()

    query = query.strip()
    
    # 1. Test if query is directly a valid SMILES string
    mol = Chem.MolFromSmiles(query)
    if mol is not None:
        try:
            canon = Chem.CanonSmiles(query)
            formula = rdMolDescriptors.CalcMolFormula(mol)
            matched = CANONICAL_SMILES_INDEX.get(canon)
            
            compound_name = matched["name"] if matched else f"Molecule ({formula})"
            return {
                "is_valid": True,
                "smiles": query,
                "canonical_smiles": canon,
                "compound_name": compound_name,
                "formula": formula,
                "mol": mol,
                "metadata": matched
            }
        except Exception:
            formula = rdMolDescriptors.CalcMolFormula(mol)
            return {
                "is_valid": True,
                "smiles": query,
                "canonical_smiles": query,
                "compound_name": f"Molecule ({formula})",
                "formula": formula,
                "mol": mol,
                "metadata": None
            }

    # 2. If not a valid SMILES, test if it's a known compound name
    smiles_from_name = lookup_by_name(query)
    if smiles_from_name:
        mol = Chem.MolFromSmiles(smiles_from_name)
        if mol is not None:
            canon = Chem.CanonSmiles(smiles_from_name)
            formula = rdMolDescriptors.CalcMolFormula(mol)
            matched = CANONICAL_SMILES_INDEX.get(canon)
            return {
                "is_valid": True,
                "smiles": smiles_from_name,
                "canonical_smiles": canon,
                "compound_name": matched["name"] if matched else query.capitalize(),
                "formula": formula,
                "mol": mol,
                "metadata": matched
            }

    # 3. Could not parse as SMILES or find in local chemical dictionary
    return {
        "is_valid": False,
        "smiles": None,
        "canonical_smiles": None,
        "compound_name": query,
        "formula": None,
        "mol": None,
        "metadata": None
    }

# Initialize at import time
init_compound_library()
