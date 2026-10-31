"""Independent editing instructions for assembling a child's drawing transformation."""

from crayonmlx.presets.styles import STYLE_DESCRIPTIONS, style_templates
from crayonmlx.schemas import Preservation, PromptTemplate

EDIT_RULES = """Use the uploaded drawing as the reference for the actual subjects. Perform the edits specified in the selected blocks. Do not invent a new protagonist, franchise characters, cat ears, lavender hair, or other identity features absent from the drawing. If the main subject is a building or landscape, keep it the main subject. Do not add people or animals unless explicitly requested. Keep the child's imaginative details recognizable. Preservation rules below constrain the requested edits; details without a preservation rule may adapt to the requested treatment. Do not add watermarks, logos, or unrelated text."""

BACKGROUNDS = {
    "Сеул": "Seoul, South Korea: a pedestrian street combining traditional hanok architecture with a distant modern skyline and mountain silhouettes.",
    "Токио": "Tokyo, Japan: a layered city street with Japanese urban architecture and recognizable metropolitan depth. Do not add crowds or readable advertising text.",
    "Париж": "Paris, France: a riverside promenade, elegant Haussmann facades, and a distant Eiffel Tower.",
    "Петербург": "Saint Petersburg, Russia: a granite canal embankment, a graceful bridge, and historic pastel facades.",
    "Нью-Йорк": "New York City: a broad street framed by recognizable Manhattan architecture and a layered skyscraper skyline.",
    "Киото": "Kyoto, Japan: a quiet lane with traditional wooden houses, stone paving, and a distant pagoda.",
    "Лес": "a beautiful forest clearing with layered tree canopies, ferns, and a winding woodland path.",
    "Горы": "a mountain valley with granite peaks, forested slopes, a rocky stream, and a stone path.",
    "Море": "a seaside landscape with a sandy shore, gentle waves, and a distant horizon.",
    "Космос": "an imaginative outer-space setting with a starfield, distant planets, and a stable surface beneath the original subjects.",
}
COMPOSITIONS = {
    "Целиком": "Frame all original main subjects completely, with comfortable space around them. For characters, include their entire bodies; for buildings, include roof and foundation. Do not crop distinctive details.",
    "Крупный план": "Create a close view of the original main subject, emphasizing its distinctive face or, for a building or object, its most characteristic details. Cropping the surrounding scene is intentional.",
    "Общий план": "Use a wide establishing composition with the original main subject clearly readable within its surroundings. Keep it the focal point without adding new protagonists.",
    "В центре": "Reframe the original main subject centrally with balanced space around it. Reposition subjects only as needed for this composition.",
    "Детские пропорции": "Retain the drawing's unusual proportions, naive perspective, relative sizes, and playful spatial relationships instead of correcting them into conventional realism.",
}
LIGHTING = {
    "Мягкий дневной": "Use soft daylight, gentle shadows, natural material response, and clear readable forms.",
    "Золотой час": "Use warm low afternoon sunlight, delicate golden rim light, long soft shadows, and atmospheric depth.",
    "Пасмурный день": "Use diffuse overcast daylight, soft ambient shadows, subtle contrast, and rich surface detail.",
    "Вечерний городской": "Use blue-hour ambient light and warm illumination motivated by existing windows or street fixtures. Do not add new foreground objects.",
    "Неоновый": "Use cinematic neon-colored reflected light with balanced warm and cool highlights. Convey the effect through illumination without adding signs or new objects.",
    "Сценический": "Use theatrical key and rim lighting, controlled contrast, and a clear focal subject. Do not add a stage, audience, or lighting equipment.",
    "Сказочное свечение": "Use a gentle magical glow, luminous edges, soft bloom, and atmospheric depth. Create the effect through light without adding creatures or magical objects.",
}
CONSTRAINTS = {
    "Только выбранные изменения": EDIT_RULES,
    "Бережно к детскому рисунку": EDIT_RULES
    + " Preserve the child's quirky shapes, asymmetry, handmade decorations, and visual humor. Do not replace their design with a generic polished character.",
    "Свободнее интерпретировать детали": EDIT_RULES
    + " You may refine small construction details and material textures to complete the requested treatment, except where preservation rules explicitly forbid changes.",
}


def default_preservation() -> Preservation:
    return Preservation(**{key: True for key in Preservation.model_fields})


def initial_templates() -> list[PromptTemplate]:
    result = style_templates()
    for name, description in STYLE_DESCRIPTIONS.items():
        result.append(
            PromptTemplate(
                name=f"Герои и объекты · {name}",
                category="subject",
                text=f"Render only the original foreground characters, animals, or main object in this treatment: {description} This overrides the overall style for these subjects only. Do not apply it to the surrounding background. Do not invent a human protagonist when none is drawn.",
            )
        )
    groups = [
        ("background", "Фон", BACKGROUNDS),
        ("composition", "Композиция", COMPOSITIONS),
        ("lighting", "Свет", LIGHTING),
        ("constraints", "Изменения", CONSTRAINTS),
    ]
    for category, prefix, entries in groups:
        for name, text in entries.items():
            if category == "background":
                text = f"Replace the original surrounding background with {text} Integrate the original main subjects naturally into this location. If a drawn house is the main subject, retain that house rather than replacing it with a landmark. Follow the separately selected rendering style and lighting."
            result.append(PromptTemplate(name=f"{prefix} · {name}", category=category, text=text))
    return result
