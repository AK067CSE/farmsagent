# Re-export all prompts from prompts.py for backward compatibility

import importlib.util
import sys

# Import prompts.py module directly without triggering the prompts package __init__
spec = importlib.util.spec_from_file_location("prompts_module", "prompts.py")
prompts_module = importlib.util.module_from_spec(spec)
sys.modules['prompts_module'] = prompts_module
spec.loader.exec_module(prompts_module)

# Now we can safely import from the module without circular import
from prompts_module import (
    WEATHER_AGENT_INSTR,
    SEARCH_AGENT_INSTR,
    DHANUKA_IMAGE_AGENT_INSTR,
    FARMING_AGENT_INSTR,
    DHANUKA_KNOWLEDGE,
    get_dhanuka_recommendations,
    format_dhanuka_recommendation,
)

# Also export the Dhanuka-specific items that agent.py imports from prompt_dhanuka
from prompts.prompt_dhanuka import (
    DHANUKA_CATALOG_TOOLING_RULES,
    DHANUKA_TEXT_ONLY_ADVISOR_INSTR,
    DHANUKA_IMAGE_ADVISOR_INSTR,
)

# Also export searcher instructions from all agent modules
# Finance & Insurance
from prompts.prompt_finance_insurance import (
    FINANCE_SEARCHER_INSTR,
    FINANCE_PLANNER_INSTR,
    FINANCE_ADVISOR_INSTR,
    FINANCE_COORDINATOR_INSTR,
)

# Post Harvest
from prompts.prompt_post_harvest import (
    POST_HARVEST_SEARCHER_INSTR,
    POST_HARVEST_PLANNER_INSTR,
    POST_HARVEST_ADVISOR_INSTR,
    POST_HARVEST_COORDINATOR_INSTR,
)

# Compliance & Safety
from prompts.prompt_compliance_safety import (
    COMPLIANCE_SAFETY_SEARCHER_INSTR,
    COMPLIANCE_SAFETY_PLANNER_INSTR,
    COMPLIANCE_SAFETY_ADVISOR_INSTR,
    COMPLIANCE_SAFETY_COORDINATOR_INSTR,
)

# Machinery & Mechanization
from prompts.prompt_machinery_mechanization import (
    MACHINERY_SEARCHER_INSTR,
    MACHINERY_PLANNER_INSTR,
    MACHINERY_ADVISOR_INSTR,
    MACHINERY_COORDINATOR_INSTR,
)

# Sustainability & Regenerative
from prompts.prompt_sustainability_regen import (
    SUSTAINABILITY_REGEN_SEARCHER_INSTR,
    SUSTAINABILITY_REGEN_PLANNER_INSTR,
    SUSTAINABILITY_REGEN_ADVISOR_INSTR,
    SUSTAINABILITY_REGEN_COORDINATOR_INSTR,
)

# Soil Analyzer
from prompts.prompt_soil_analyzer import (
    SOIL_ANALYZER_SEARCHER_INSTR,
    SOIL_ANALYZER_PLANNER_INSTR,
    SOIL_ANALYZER_ADVISOR_INSTR,
    SOIL_ANALYZER_COORDINATOR_INSTR,
)

# Marketing Agent
from prompts.prompt_marketing_agent import (
    MARKETING_SEARCHER_INSTR,
    MARKETING_PLANNER_INSTR,
    MARKETING_ADVISOR_INSTR,
    MARKETING_COORDINATOR_INSTR,
)

# Crop Doctor
from prompts.prompt_crop_doctor import (
    CROP_DOCTOR_SEARCHER_INSTR,
    CROP_DOCTOR_PLANNER_INSTR,
    CROP_DOCTOR_ADVISOR_INSTR,
    CROP_DOCTOR_COORDINATOR_INSTR,
)

# Plant Growth
from prompts.prompt_plant_growth import (
    PLANT_GROWTH_SEARCHER_INSTR,
    PLANT_GROWTH_PLANNER_INSTR,
    PLANT_GROWTH_ADVISOR_INSTR,
    PLANT_GROWTH_COORDINATOR_INSTR,
)

# Crop Planning
from prompts.prompt_crop_planning import (
    CROP_PLANNER_INSTR,
    CROP_SEARCHER_INSTR,
    CROP_ADVISOR_INSTR,
    CROP_COORDINATOR_INSTR,
)

# Weather
from prompts.prompt_weather import (
    WEATHER_PLANNER_INSTR,
    WEATHER_SEARCHER_INSTR,
    WEATHER_ADVISOR_INSTR,
    WEATHER_COORDINATOR_INSTR,
)

# Mandi
from prompts.prompt_mandi import (
    MANDI_PLANNER_INSTR,
    MANDI_SEARCHER_INSTR,
    MANDI_ADVISOR_INSTR,
    MANDI_COORDINATOR_INSTR,
)

# Schemes
from prompts.prompt_schemes import (
    SCHEMES_PLANNER_INSTR,
    SCHEMES_SEARCHER_INSTR,
    SCHEMES_ADVISOR_INSTR,
    SCHEMES_COORDINATOR_INSTR,
)

# Fertilizer & Soil
from prompts.prompt_fertilizer_soil import (
    FERTILIZER_PLANNER_INSTR,
    FERTILIZER_SEARCHER_INSTR,
    FERTILIZER_ADVISOR_INSTR,
    FERTILIZER_COORDINATOR_INSTR,
)

# Pest & Disease
from prompts.prompt_pest_disease import (
    PEST_PLANNER_INSTR,
    PEST_SEARCHER_INSTR,
    PEST_ADVISOR_INSTR,
    PEST_COORDINATOR_INSTR,
)

# Backward compatibility aliases for old naming convention
FINANCE_INSURANCE_SEARCHER_INSTR = FINANCE_SEARCHER_INSTR
FINANCE_INSURANCE_PLANNER_INSTR = FINANCE_PLANNER_INSTR
FINANCE_INSURANCE_ADVISOR_INSTR = FINANCE_ADVISOR_INSTR
FINANCE_INSURANCE_COORDINATOR_INSTR = FINANCE_COORDINATOR_INSTR

MACHINERY_MECHANIZATION_SEARCHER_INSTR = MACHINERY_SEARCHER_INSTR
MACHINERY_MECHANIZATION_PLANNER_INSTR = MACHINERY_PLANNER_INSTR
MACHINERY_MECHANIZATION_ADVISOR_INSTR = MACHINERY_ADVISOR_INSTR
MACHINERY_MECHANIZATION_COORDINATOR_INSTR = MACHINERY_COORDINATOR_INSTR

# Export all prompt modules for convenience
from prompts import prompt_weather
from prompts import prompt_dhanuka
from prompts import prompt_orchestrator
from prompts import prompt_fertilizer_soil
from prompts import prompt_schemes
from prompts import prompt_machinery_mechanization
from prompts import prompt_soil_analyzer
from prompts import prompt_marketing_agent
from prompts import prompt_mandi
from prompts import prompt_finance_insurance
from prompts import prompt_post_harvest
from prompts import prompt_pest_disease
from prompts import prompt_crop_doctor
from prompts import prompt_crop_planning
from prompts import prompt_plant_growth
from prompts import prompt_image_diagnosis
from prompts import prompt_compliance_safety
from prompts import prompt_sustainability_regen
from prompts import prompt_irrigation
