from discovery.filters import evaluate


def test_tier1_english_match():
    result = evaluate("We build AI for engineering workflows.")
    assert result.passes_tier1 is True
    assert "ai_engineering" in result.matched_tier1


def test_tier1_german_match():
    result = evaluate("Unsere Plattform optimiert Verbundwerkstoffe für Leichtbau.")
    assert result.passes_tier1 is True
    assert "composite_materials" in result.matched_tier1


def test_tier1_no_match():
    result = evaluate("We sell shoes and coffee.")
    assert result.passes_tier1 is False


def test_tier2_score():
    result = evaluate("AI for engineering with Ansys and CFD workflows")
    assert result.tier2_score == 2


def test_tier3_tool_extraction():
    result = evaluate("We use PyTorch and Abaqus for structural mechanics.")
    assert set(result.tier3_tools) == {"PyTorch", "Abaqus"}


def test_confidence_low_when_no_tier2():
    result = evaluate("AI for engineering for manufacturing teams")
    assert result.confidence == "low"


def test_confidence_high_when_tier2_present():
    result = evaluate("AI for engineering with CFD-driven design loops")
    assert result.confidence == "high"


def test_case_insensitive():
    result = evaluate("VERBUNDWERKSTOFFE for aerospace")
    assert result.passes_tier1 is True
