"""Drawing-preserving style presets shared by both editable libraries."""

from crayonmlx.schemas import Preset, PromptBlocks, PromptTemplate

SOURCE_RULES = """Use the uploaded image as the source of truth for the subject and composition. Preserve the actual characters, animals, buildings, objects, clothing, colors, poses, and their arrangement shown in this image.

If the drawing contains a house or landscape, make that house or landscape the main subject. Include people or animals only when they are present in the uploaded drawing. Preserve distinctive details and decorations.

Do not introduce a new protagonist, cat ears, lavender hair, or any other character features unless they are visible in the uploaded image. Do not add franchise characters, new objects, text, logos, or watermarks. Preserve any intentional lettering or decorations already present in the drawing.

Create a complete finished scene, preserving the imagination and personality of the original drawing."""

HUNTRIX = """Transform the uploaded drawing into a polished cinematic 3D animated illustration with the visual aesthetic of a high-budget musical fantasy adventure.

Use the uploaded image as the source of truth for the subject and composition. Preserve the actual characters, animals, buildings, objects, clothing, colors, poses, and their arrangement shown in this image.

Give the scene expressive shapes, detailed materials, rich colors, soft cinematic lighting, atmospheric depth, and a beautifully finished animated-film appearance.

If the drawing contains a house or landscape, make that house or landscape the main subject. Include people or animals only when they are present in the uploaded drawing. Preserve distinctive details and decorations.

Do not introduce a new protagonist, cat ears, lavender hair, or any other character features unless they are visible in the uploaded image.

Create a complete finished scene, preserving the imagination and personality of the original drawing."""

# Each description changes rendering, not the contents of the source drawing.
STYLE_DESCRIPTIONS = {
    "Roblox": "Transform the uploaded drawing into a polished Roblox-style 3D illustration. Reinterpret the existing subjects using blocky geometry, simple readable silhouettes, clean toy-like materials, and playful game-world lighting. Use recognizable Roblox-like proportions only for people already present. Preserve the original colors, decorations, poses, and layout; do not add an avatar or a game interface.",
    "Аниме": "Transform the uploaded drawing into a beautifully finished 2D anime illustration. Use expressive linework, refined cel shading, carefully painted backgrounds, rich harmonious colors, and cinematic composition. Stylize existing faces expressively while retaining their identity. Render buildings, animals, and landscapes with equal care; do not turn objects into people.",
    "Studio Ghibli": "Transform the uploaded drawing into a richly hand-painted animated-film illustration in the style of Studio Ghibli. Use warm, natural colors, delicate linework, soft painted light, tactile everyday materials, and atmospheric depth. Give the existing scene a gentle sense of wonder through rendering and lighting. Keep the original setting and subjects; do not add creatures, vegetation, buildings, or characters that are absent from the drawing.",
    "Реалистичная живопись": "Transform the uploaded drawing into a finished realistic oil painting. Use convincing perspective, carefully observed forms, natural light, nuanced color transitions, visible but refined brushwork, and subtle canvas texture. Interpret the drawn subjects as believable painted forms while preserving their distinctive shapes and colors. Keep imaginative elements intact rather than replacing them with ordinary real-world substitutes.",
    "Disney": "Transform the uploaded drawing into a polished Disney-style animated-film illustration. Use appealing expressive shapes, elegant silhouettes, detailed materials, rich harmonious colors, soft cinematic lighting, and a magical storybook finish. Apply the animated-film aesthetic to the actual subjects in the drawing, including houses or landscapes when they are the focus. Do not add a princess, sidekick, or castle.",
    "Disney · Frozen": "Transform the uploaded drawing into a polished 3D animated-film illustration with the elegant sculpted shapes, delicate material detail, luminous lighting, and refined cinematic finish associated with Disney's Frozen. Preserve the source colors and setting. Do not introduce snow, ice, winter clothing, or Frozen characters unless those elements are already present in the drawing.",
    "Disney · Encanto": "Transform the uploaded drawing into a vibrant 3D animated-film illustration with the expressive forms, lovingly detailed surfaces, rich color relationships, and warm cinematic lighting associated with Disney's Encanto. Celebrate the existing architecture, clothing, and decorations without changing their identity. Do not add a magical house, flowers, tropical scenery, or Encanto characters unless present in the original drawing.",
    "Pixar": "Transform the uploaded drawing into a polished Pixar-style 3D animated-film illustration. Use appealing sculpted forms, expressive existing characters, tactile materials, nuanced color design, soft global illumination, and cinematic depth. Give buildings, animals, and objects the same care as people. Preserve the original subject and arrangement without adding a new protagonist or anthropomorphizing objects.",
    "Pixar · Soul": "Transform the uploaded drawing into a polished 3D animated-film illustration with the expressive sculpted forms, painterly color design, subtle material detail, and atmospheric cinematic lighting associated with Pixar's Soul. Preserve the original colors, subjects, and location. Do not turn subjects into blue spirits or introduce musicians, musical instruments, city streets, or Soul characters unless visible in the original drawing.",
    "Пиксель-арт": "Transform the uploaded drawing into a beautifully finished pixel-art illustration. Use a consistent pixel grid, crisp hard-edged pixel clusters, a controlled palette derived from the drawing, deliberate dithering, and carefully designed pixel-level highlights and shadows. Keep every main subject readable and preserve the whole composition. No smooth vector edges, blur, photographic textures, or game interface.",
}


def style_presets() -> list[Preset]:
    prompts = {"Хантрик": HUNTRIX}
    prompts.update({name: f"{description}\n\n{SOURCE_RULES}" for name, description in STYLE_DESCRIPTIONS.items()})
    return [Preset(name=name, blocks=PromptBlocks(style=text)) for name, text in prompts.items()]


def style_templates() -> list[PromptTemplate]:
    return [
        PromptTemplate(name=f"Стиль · {preset.name}", category="style", text=preset.blocks.style)
        for preset in style_presets()
    ]
