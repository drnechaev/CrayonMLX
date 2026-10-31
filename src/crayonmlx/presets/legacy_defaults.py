"""Editable starting points, copied to application data on first launch."""

from crayonmlx.presets.legacy_styles import style_presets
from crayonmlx.schemas import Parameters, Preset, PromptBlocks


def initial_presets() -> list[Preset]:
    cinematic = PromptBlocks(
        style="Transform the character in the uploaded drawing into a polished cinematic 3D animated heroine. Use the drawing as the primary reference for her identity, hairstyle, expression, clothing, and colors. Create the look of a high-budget animated fantasy film: an expressive stylized face, large appealing eyes, delicate facial features, softly shaded skin, beautifully sculpted hair, detailed fabric, and cinematic lighting. Use elegant cartoon proportions with a slightly enlarged head and natural anatomy. The result should feel like a finished animated movie frame rather than a photograph, a flat anime illustration, or a plastic toy.",
        subject="Preserve these character details: pale lavender hair with thick, shaggy layers and pointed locks that flare outward, reaching just below her shoulders. Two lavender cat ears with soft pink interiors. Closed smiling eyes with long dark eyelashes, rosy cheeks, and a small, sweet catlike smile. A plain white long-sleeved turtleneck sweater, blue jeans, and gray-white sneakers with dark crossed laces. A relaxed standing pose with one knee slightly bent and both arms resting naturally at her sides.",
        background="Place her in a beautiful South Korean mountain landscape: dramatic granite peaks, forested slopes, graceful pine trees, flowering azaleas, and a clear rocky stream with small waterfalls. She stands on a sunlit stone path beside the water. Add soft mountain mist and warm afternoon sunlight.",
        composition="Frame the entire character from the tips of her ears to the soles of her shoes, with comfortable space around her. Keep her face and clothing sharp, with atmospheric depth in the landscape. Use soft golden rim lighting on her lavender hair, gentle shadows, and rich, harmonious colors.",
        constraints="Keep the original character recognizable. Give her exactly two arms, two hands, and two legs, with anatomically coherent joints and fingers. Do not add pets, weapons, jewelry, clothing graphics, text, logos, or watermarks.",
    )
    return style_presets() + [
        Preset(name="Героиня анимационного фильма", blocks=cinematic),
        Preset(
            name="Рисунок оживает",
            blocks=PromptBlocks(
                style="Transform the uploaded drawing into a polished cinematic 3D animation frame with soft lighting and expressive characters.",
                subject="Preserve the identity, colors, clothing, expression and distinctive details of the original drawing.",
                background="A beautiful, magical woodland with warm afternoon sunlight.",
                composition="Show the entire subject with comfortable space around it. Preserve the original pose.",
                constraints="Keep the original recognizable. Coherent anatomy. No text, logos or watermarks.",
            ),
        ),
        Preset(
            name="Акварельная сказка",
            blocks=PromptBlocks(
                style="Turn this drawing into a delicate watercolor illustration for a children's storybook. Textured paper, soft pigments, warm harmonious colors.",
                subject="Preserve the original character's identity, silhouette, colors and expression.",
                composition="Keep the original composition and the whole character visible.",
                constraints="No text, logos or watermarks. Coherent anatomy.",
            ),
            parameters=Parameters(guidance=2.5),
        ),
    ]
