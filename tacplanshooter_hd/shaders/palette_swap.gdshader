shader_type canvas_item;

uniform vec4 squad_color : source_color = vec4(1.0);
uniform vec4 trim_color : source_color = vec4(1.0);
uniform vec4 armor_color : source_color = vec4(1.0);
uniform vec4 optic_color : source_color = vec4(1.0);

const vec3 KEY_PRIMARY = vec3(1.0, 0.0, 1.0);
const vec3 KEY_SECONDARY = vec3(0.0, 1.0, 1.0);
const vec3 KEY_ARMOR = vec3(1.0, 1.0, 0.0);
const vec3 KEY_OPTIC = vec3(0.0, 1.0, 0.0);

void fragment() {
	vec4 base = texture(TEXTURE, UV);
	if (length(base.rgb - KEY_PRIMARY) < 0.15) {
		base = squad_color;
	} else if (length(base.rgb - KEY_SECONDARY) < 0.15) {
		base = trim_color;
	} else if (length(base.rgb - KEY_ARMOR) < 0.15) {
		base = armor_color;
	} else if (length(base.rgb - KEY_OPTIC) < 0.15) {
		base = optic_color;
	}
	COLOR = base;
}
