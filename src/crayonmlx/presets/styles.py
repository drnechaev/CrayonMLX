"""Rendering treatments: no scene, identity, framing, or preservation policy."""

from crayonmlx.schemas import PromptTemplate

STYLE_DESCRIPTIONS = {
    "Хантрик": "A polished cinematic 3D animated illustration with the visual aesthetic of a high-budget musical fantasy adventure. Expressive shapes, detailed materials, rich colors, and a beautifully finished animated-film appearance.",
    "Roblox": "A polished Roblox-style 3D illustration with blocky geometry, clean toy-like materials, simple readable silhouettes, and a playful game-world finish. No game interface.",
    "Аниме": "A beautifully finished 2D anime illustration with expressive linework, refined cel shading, carefully painted surfaces, and harmonious colors.",
    "Studio Ghibli": "A richly hand-painted animated-film illustration in the style of Studio Ghibli: delicate linework, tactile materials, painterly surfaces, and a gentle sense of wonder.",
    "Реалистичная живопись": "A finished realistic oil painting with carefully observed forms, nuanced color transitions, refined visible brushwork, and subtle canvas texture. Preserve imaginative drawn forms rather than replacing them with ordinary substitutes.",
    "Disney": "A polished Disney-style animated-film illustration with appealing expressive shapes, elegant silhouettes, detailed materials, and a magical storybook finish.",
    "Disney · Frozen": "An elegant 3D animated-film finish inspired by Disney's Frozen, with sculpted shapes and delicate material detail. This is a rendering treatment, not a request for snow, ice, or franchise characters.",
    "Disney · Encanto": "A vibrant 3D animated-film finish inspired by Disney's Encanto, with expressive forms, lovingly detailed surfaces, and rich color relationships. Do not import the film's characters or setting.",
    "Pixar": "A polished Pixar-style 3D animated-film illustration with appealing sculpted forms, tactile materials, nuanced color design, and beautifully finished surfaces.",
    "Pixar · Soul": "A refined 3D animated-film finish inspired by Pixar's Soul, with expressive sculpted forms, painterly color design, and subtle material detail. This does not request blue spirits, musicians, or the film's setting.",
    "Пиксель-арт": "A finished pixel-art illustration with a consistent pixel grid, crisp hard-edged clusters, deliberate dithering, and carefully designed pixel-level highlights and shadows. No blur, smooth vector edges, photographic texture, or game interface.",
}


def style_templates() -> list[PromptTemplate]:
    return [
        PromptTemplate(
            name=f"Стиль · {name}",
            category="style",
            text=f"Overall rendering style: {description} Apply separately selected subject, background, composition, and lighting instructions; a subject-specific rendering treatment takes precedence for those subjects only.",
        )
        for name, description in STYLE_DESCRIPTIONS.items()
    ]
