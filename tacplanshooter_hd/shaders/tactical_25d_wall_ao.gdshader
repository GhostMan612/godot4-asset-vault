shader_type canvas_item;

uniform float ao_strength : hint_range(0.0, 1.0) = 0.42;
uniform float top_rim_boost : hint_range(0.0, 0.5) = 0.14;
uniform vec4 shadow_tint : source_color = vec4(0.04, 0.06, 0.10, 1.0);

void fragment() {
    vec4 tex = texture(TEXTURE, UV);
    float bottom_ao = smoothstep(0.65, 1.0, UV.y) * ao_strength;
    float top_rim = (1.0 - smoothstep(0.0, 0.14, UV.y)) * top_rim_boost;
    vec3 col = mix(tex.rgb, shadow_tint.rgb, bottom_ao) + vec3(top_rim);
    COLOR = vec4(col, tex.a);
}
