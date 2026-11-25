shader_type canvas_item;

uniform float intensity : hint_range(0.0, 0.08) = 0.015;
uniform float speed = 9.0;

void fragment() {
    float band = step(0.82, fract(sin(floor(UV.y * 28.0) * 12.9898 + floor(TIME * speed) * 78.233) * 43758.5453));
    vec2 uv = UV + vec2(band * intensity, 0.0);
    vec4 tex = texture(TEXTURE, uv);
    COLOR = vec4(tex.rgb + vec3(0.45, 0.22, 0.05) * band * tex.a, tex.a);
}
