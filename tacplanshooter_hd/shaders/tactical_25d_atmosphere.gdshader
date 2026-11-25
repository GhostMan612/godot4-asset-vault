shader_type canvas_item;

uniform float vignette_strength : hint_range(0.0, 1.0) = 0.38;
uniform float vignette_softness : hint_range(0.1, 1.0) = 0.55;
uniform vec4 tint_color : source_color = vec4(0.04, 0.07, 0.11, 1.0);

void fragment() {
    float dist = distance(UV, vec2(0.5));
    float vig = smoothstep(0.75 - vignette_softness, 0.85, dist) * vignette_strength;
    COLOR = vec4(tint_color.rgb, vig);
}
