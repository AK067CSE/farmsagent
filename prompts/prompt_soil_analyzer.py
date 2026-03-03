"""KisanMitra Soil Analyzer — Short answers."""
# =============================================================================
SOIL_ANALYZER_PLANNER_INSTR = '''
Extract: location, crop. Keep queries short.
'''

# =============================================================================
SOIL_ANALYZER_SEARCHER_INSTR = '''
Short output. Max 5 lines.
'''

# =============================================================================
SOIL_ANALYZER_ADVISOR_INSTR = '''
Short answers. Max 100 words.

For soil testing centers:
- State agriculture dept
- Nearest KVK
- Soil Health Card portal

Keep answer under 5 lines.
'''

# =============================================================================
SOIL_ANALYZER_COORDINATOR_INSTR = '''
Max 100 words total.
'''

__all__ = ["SOIL_ANALYZER_PLANNER_INSTR", "SOIL_ANALYZER_SEARCHER_INSTR",
           "SOIL_ANALYZER_ADVISOR_INSTR", "SOIL_ANALYZER_COORDINATOR_INSTR"]
