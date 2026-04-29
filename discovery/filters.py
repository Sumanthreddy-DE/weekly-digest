from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FilterResult:
    passes_tier1: bool
    matched_tier1: list[str]
    tier2_score: int
    tier3_tools: list[str]
    confidence: str


TIER1_EN_DE = {
    "ai_engineering": ["AI for engineering", "KI im Ingenieurwesen"],
    "ml_simulation": ["machine learning for simulation", "maschinelles Lernen Simulation"],
    "physics_informed_ml": ["physics-informed machine learning", "physik-informiertes maschinelles Lernen"],
    "ai_cae": ["AI-driven CAE", "KI-gestützte CAE", "AI for CAE"],
    "ai_cad": ["AI for CAD", "KI für CAD"],
    "computational_engineering_ai": ["computational engineering AI", "rechnergestützte Konstruktion KI"],
    "digital_twin": ["digital twin", "digitaler Zwilling"],
    "generative_design": ["generative design", "generatives Design"],
    "topology_opt_ai": ["topology optimization AI", "KI Topologieoptimierung"],
    "structural_mechanics": ["structural mechanics", "Strukturmechanik"],
    "structural_engineering": ["structural engineering", "Bauingenieurwesen", "Tragwerksplanung"],
    "fea_software": ["FEA software", "FEM Software"],
    "finite_element": ["finite element analysis", "Finite-Elemente-Analyse"],
    "mechanical_reasoning": ["mechanical reasoning", "mechanisches Schließen"],
    "component_design": ["component design", "Bauteilauslegung"],
    "assembly_design": ["assembly design", "Baugruppenkonstruktion"],
    "homogenization": ["homogenization", "Homogenisierung"],
    "composite_materials": ["composite materials", "Verbundwerkstoffe", "Composites"],
    "fiber_composites": ["fiber-reinforced composites", "faserverstärkte Verbundwerkstoffe", "CFRP", "CFK"],
    "lightweight": ["lightweight structures", "Leichtbau", "Leichtbaustrukturen"],
    "aerospace": ["aerospace", "Luft- und Raumfahrt"],
    "aircraft_structures": ["aircraft structures", "Flugzeugstrukturen"],
    "injection_moulding": ["injection moulding", "Spritzguss"],
    "plastics_engineering": ["plastics engineering", "Kunststofftechnik"],
    "manufacturing_ai": ["manufacturing AI", "KI in der Fertigung"],
    "industrialization": ["industrialization", "Industrialisierung"],
    "production_engineering": ["production engineering", "Produktionstechnik"],
    "prototype_design": ["prototype design", "Prototypenentwicklung"],
    "hydraulics": ["hydraulics", "Hydraulik"],
    "packaging": ["packaging industry", "Verpackungsindustrie"],
}

TIER2 = [
    "physics simulation",
    "CFD",
    "mesh generation",
    "FEA",
    "FEM",
    "multi-physics",
    "CAD",
    "CAE",
    "PLM",
    "MBSE",
    "Ansys",
    "Creo",
    "NX",
    "Solidworks",
    "Abaqus",
    "COMSOL",
    "OpenFOAM",
    "Simcenter",
    "generative AI for design",
    "neural surrogate",
    "surrogate model",
    "materials informatics",
    "materials genomics",
]

TIER3_TOOLS = [
    "Ansys",
    "Creo",
    "NX",
    "Solidworks",
    "Abaqus",
    "COMSOL",
    "OpenFOAM",
    "Simcenter",
    "MATLAB",
    "PyTorch",
    "JAX",
    "TensorFlow",
]

CONFIDENCE_THRESHOLD = 1


def evaluate(text: str) -> FilterResult:
    haystack = text.lower()
    matched = [
        key
        for key, variants in TIER1_EN_DE.items()
        if any(variant.lower() in haystack for variant in variants)
    ]
    tier2_hits = sum(1 for keyword in TIER2 if keyword.lower() in haystack)
    tools = [tool for tool in TIER3_TOOLS if tool.lower() in haystack]
    return FilterResult(
        passes_tier1=bool(matched),
        matched_tier1=matched,
        tier2_score=tier2_hits,
        tier3_tools=tools,
        confidence="high" if tier2_hits >= CONFIDENCE_THRESHOLD else "low",
    )
