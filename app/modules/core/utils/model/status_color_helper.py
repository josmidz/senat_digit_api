from enum import Enum
from typing import Type, Dict, List, Optional, Literal
import hashlib
from pydantic import BaseModel, Field as PydanticField

# Define allowed color keys as a literal type with many more options
ColorPaletteName = Literal[
    "green", "blue", "orange", "purple", "red", "gray",
    "teal", "cyan", "indigo", "pink", "brown", "lime",
    "yellow", "amber", "deep_orange", "deep_purple", 
    "light_blue", "light_green", "light_cyan", "light_pink", "blue_gray", "black", "white"
]

class ColorMapping(BaseModel):
    """Pydantic model to validate color mappings with extensive color options"""
    green: List[str] = PydanticField(default_factory=list)
    blue: List[str] = PydanticField(default_factory=list)
    orange: List[str] = PydanticField(default_factory=list)
    purple: List[str] = PydanticField(default_factory=list)
    red: List[str] = PydanticField(default_factory=list)
    gray: List[str] = PydanticField(default_factory=list)
    teal: List[str] = PydanticField(default_factory=list)
    cyan: List[str] = PydanticField(default_factory=list)
    indigo: List[str] = PydanticField(default_factory=list)
    pink: List[str] = PydanticField(default_factory=list)
    brown: List[str] = PydanticField(default_factory=list)
    lime: List[str] = PydanticField(default_factory=list)
    yellow: List[str] = PydanticField(default_factory=list)
    amber: List[str] = PydanticField(default_factory=list)
    deep_orange: List[str] = PydanticField(default_factory=list)
    deep_purple: List[str] = PydanticField(default_factory=list)
    light_blue: List[str] = PydanticField(default_factory=list)
    light_green: List[str] = PydanticField(default_factory=list)
    light_cyan: List[str] = PydanticField(default_factory=list)
    light_pink: List[str] = PydanticField(default_factory=list)
    blue_gray: List[str] = PydanticField(default_factory=list)
    black: List[str] = PydanticField(default_factory=list)
    white: List[str] = PydanticField(default_factory=list)
    

class StatusColorHelper:
    """Helper class for generating consistent status colors for enums with extensive palette."""
    
    # Extensive color palettes (Material Design inspired)
    COLOR_PALETTES: Dict[ColorPaletteName, List[tuple]] = {
        # Greens
        "green": [("4CAF50", "E8F5E9"), ("2E7D32", "C8E6C9"), ("1B5E20", "A5D6A7"), ("388E3C", "C8E6C9")],
        
        # Blues
        "blue": [("2196F3", "E3F2FD"), ("1565C0", "BBDEFB"), ("0D47A1", "90CAF9"), ("1976D2", "BBDEFB")],
        
        # Oranges
        "orange": [("FF9800", "FFF3E0"), ("F57C00", "FFE0B2"), ("E65100", "FFCC80"), ("EF6C00", "FFE0B2")],
        
        # Purples
        "purple": [("9C27B0", "F3E5F5"), ("7B1FA2", "E1BEE7"), ("4A148C", "CE93D8"), ("6A1B9A", "E1BEE7")],
        
        # Reds
        "red": [("F44336", "FFEBEE"), ("D32F2F", "FFCDD2"), ("B71C1C", "EF9A9A"), ("C62828", "FFCDD2")],
        
        # Grays
        "gray": [("757575", "F5F5F5"), ("616161", "EEEEEE"), ("424242", "E0E0E0"), ("9E9E9E", "F5F5F5")],
        
        # Teals
        "teal": [("009688", "E0F2F1"), ("00897B", "B2DFDB"), ("00695C", "80CBC4"), ("00796B", "B2DFDB")],
        
        # Cyans
        "cyan": [("00BCD4", "E0F7FA"), ("0097A7", "B2EBF2"), ("00838F", "80DEEA"), ("0097A7", "B2EBF2")],
        
        # Indigos
        "indigo": [("3F51B5", "E8EAF6"), ("303F9F", "C5CAE9"), ("1A237E", "9FA8DA"), ("3949AB", "C5CAE9")],
        
        # Pinks
        "pink": [("E91E63", "FCE4EC"), ("C2185B", "F8BBD0"), ("880E4F", "F48FB1"), ("D81B60", "F8BBD0")],
        
        # Browns
        "brown": [("795548", "EFEBE9"), ("5D4037", "D7CCC8"), ("4E342E", "BCAAA4"), ("6D4C41", "D7CCC8")],
        
        # Limes
        "lime": [("CDDC39", "F9FBE7"), ("AFB42B", "F0F4C3"), ("827717", "E6EE9C"), ("9E9D24", "F0F4C3")],
        
        # Yellows
        "yellow": [("FFEB3B", "FFFDE7"), ("FBC02D", "FFF9C4"), ("F9A825", "FFF59D"), ("FDD835", "FFF9C4")],
        
        # Ambers
        "amber": [("FFC107", "FFF8E1"), ("FFA000", "FFECB3"), ("FF8F00", "FFE082"), ("FFB300", "FFECB3")],
        
        # Deep Oranges
        "deep_orange": [("FF5722", "FBE9E7"), ("E64A19", "FFCCBC"), ("BF360C", "FFAB91"), ("D84315", "FFCCBC")],
        
        # Deep Purples
        "deep_purple": [("673AB7", "EDE7F6"), ("5E35B1", "D1C4E9"), ("4527A0", "B39DDB"), ("512DA8", "D1C4E9")],
        
        # Light Blues
        "light_blue": [("03A9F4", "E1F5FE"), ("0288D1", "B3E5FC"), ("01579B", "81D4FA"), ("039BE5", "B3E5FC")],
        
        # Light Greens
        "light_green": [("8BC34A", "F1F8E9"), ("689F38", "DCEDC8"), ("33691E", "C5E1A5"), ("7CB342", "DCEDC8")],
        
        # Light Cyans
        "light_cyan": [("84FFFF", "E0FFFF"), ("18FFFF", "E0FFFF"), ("00E5FF", "E0FFFF"), ("00B8D4", "E0FFFF")],
        
        # Light Pinks
        "light_pink": [("FF80AB", "FCE4EC"), ("FF4081", "F8BBD0"), ("F50057", "F8BBD0"), ("C51162", "FCE4EC")],
        
        # Blue Grays
        "blue_gray": [("607D8B", "ECEFF1"), ("455A64", "CFD8DC"), ("263238", "B0BEC5"), ("546E7A", "CFD8DC")],
        
        # Black and White (special cases)
        "black": [("000000", "F5F5F5"), ("212121", "EEEEEE")],  # Black text on light backgrounds
        "white": [("FFFFFF", "424242"), ("FAFAFA", "616161")],  # White text on dark backgrounds
    }

    @classmethod
    def get_status_color(
        cls,
        status_value,
        color_mapping: Optional[Dict[ColorPaletteName, List[str]]] = None,
        default_color: ColorPaletteName = "blue",
    ) -> Dict[str, str]:
        """
        Return a single status color object for the provided status value.
        The result contains hex codes (without leading '#') for text and background colors.

        Args:
            status_value: Enum or string status value (e.g., 'active')
            color_mapping: Optional mapping of palette name -> list of status values
            default_color: Palette to use when no mapping matches

        Returns:
            { "textColor": "HEX", "backgroundColor": "HEX" }
        """
        # Normalize value
        try:
            value = status_value.value if hasattr(status_value, "value") else str(status_value)
            value = value.lower()
        except Exception:
            value = str(status_value)

        # Try to read status_colors from SysUserModel field metadata and parse it first
        try:
            from app.modules.core.models.sys_user.sys_user_model import SysUserModel  # local import to avoid circular
            field_info = getattr(SysUserModel, "model_fields", {}).get("account_status")
            json_extra = getattr(field_info, "json_schema_extra", None) if field_info else None
            if isinstance(json_extra, dict):
                extra_metas = json_extra.get("extra_metas") or {}
                status_colors_str = extra_metas.get("status_colors")
                if isinstance(status_colors_str, str) and status_colors_str:
                    # Parse the string: "<value,text,bg>,<value2,text2,bg2>,..."
                    items = status_colors_str.split('>,<')
                    for raw in items:
                        clean = raw.strip()
                        if clean.startswith('<'):
                            clean = clean[1:]
                        if clean.endswith('>'):
                            clean = clean[:-1]
                        parts = [p.strip() for p in clean.split(',')]
                        if len(parts) == 3:
                            v, tc, bg = parts[0].lower(), parts[1].lstrip('#'), parts[2].lstrip('#')
                            if v == value:
                                return {"textColor": tc, "backgroundColor": bg}
        except Exception:
            # Silent fallback if any issue occurs when introspecting model metadata
            pass

        # Prepare mapping and choose palette (fallback)
        validated_mapping = ColorMapping(**(color_mapping or {}))
        palette_name: ColorPaletteName = default_color  # type: ignore

        # First, try provided mapping
        for name, values in validated_mapping.model_dump().items():
            if value in (values or []):
                palette_name = name  # type: ignore
                break
        else:
            # Fallback mapping for common statuses
            fallback_map: Dict[str, ColorPaletteName] = {
                # Account statuses
                "active": "green",
                "inactive": "yellow",
                "locked": "blue",
                "suspended": "red",
                "revoqued": "red",
                "locked_by_system": "black",
                # Generic global statuses
                "validated": "green",
                "pending": "orange",
                "pending_validation": "orange",
                "processing": "blue",
                "rejected": "red",
                "cancelled": "purple",
                "completed": "green",
                "frozen": "blue_gray",
                "none": "gray",
            }
            palette_name = fallback_map.get(value, default_color)  # type: ignore

        # Resolve palette and pick a consistent color pair
        palette = cls.COLOR_PALETTES.get(palette_name, cls.COLOR_PALETTES[default_color])
        import hashlib as _hashlib
        idx = int(_hashlib.md5(value.encode()).hexdigest(), 16) % len(palette)
        text_color, bg_color = palette[idx]

        # Ensure no leading '#'
        text_color = text_color.lstrip('#')
        bg_color = bg_color.lstrip('#')

        return {"textColor": text_color, "backgroundColor": bg_color}
    
    @classmethod
    def generate_status_colors(
        cls,
        enum_class: Type[Enum],
        color_mapping: Optional[Dict[ColorPaletteName, List[str]]] = None,
        default_color: ColorPaletteName = "blue"
    ) -> str:
        """Generate status colors with extensive color options."""
        validated_mapping = ColorMapping(**(color_mapping or {}))
        
        schemes = []
        used_colors = {}
        
        for enum_member in enum_class:
            value = enum_member.value
            
            # Find which color palette to use
            color_name = default_color
            for palette_name in validated_mapping.dict().keys():
                values = getattr(validated_mapping, palette_name)
                if value in values:
                    color_name = palette_name  # type: ignore
                    break
            
            # Get or create consistent color for this value
            if color_name not in used_colors:
                used_colors[color_name] = {}
            
            if value not in used_colors[color_name]:
                palette = cls.COLOR_PALETTES[color_name]
                hash_val = int(hashlib.md5(value.encode()).hexdigest(), 16)
                color_index = hash_val % len(palette)
                text_color, bg_color = palette[color_index]
                used_colors[color_name][value] = (text_color, bg_color)
            else:
                text_color, bg_color = used_colors[color_name][value]
            
            schemes.append(f"<{value},{text_color},{bg_color}>")
        
        return ",".join(schemes)
    
    @classmethod
    def create_mapping(
        cls,
        green: List[str] = None,
        blue: List[str] = None,
        orange: List[str] = None,
        purple: List[str] = None,
        red: List[str] = None,
        gray: List[str] = None,
        teal: List[str] = None,
        cyan: List[str] = None,
        indigo: List[str] = None,
        pink: List[str] = None,
        brown: List[str] = None,
        lime: List[str] = None,
        yellow: List[str] = None,
        amber: List[str] = None,
        deep_orange: List[str] = None,
        deep_purple: List[str] = None,
        light_blue: List[str] = None,
        light_green: List[str] = None,
        light_cyan: List[str] = None,
        light_pink: List[str] = None,
        blue_gray: List[str] = None,
        black: List[str] = None,
        white: List[str] = None
    ) -> Dict[ColorPaletteName, List[str]]:
        """Helper method to create color mapping with all available colors."""
        return {
            "green": green or [],
            "blue": blue or [],
            "orange": orange or [],
            "purple": purple or [],
            "red": red or [],
            "gray": gray or [],
            "teal": teal or [],
            "cyan": cyan or [],
            "indigo": indigo or [],
            "pink": pink or [],
            "brown": brown or [],
            "lime": lime or [],
            "yellow": yellow or [],
            "amber": amber or [],
            "deep_orange": deep_orange or [],
            "deep_purple": deep_purple or [],
            "light_blue": light_blue or [],
            "light_green": light_green or [],
            "light_cyan": light_cyan or [],
            "light_pink": light_pink or [],
            "blue_gray": blue_gray or [],
            "black": black or [],
            "white": white or []
        }

# Usage examples with the expanded palette
class EStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive" 
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DRAFT = "draft"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

if __name__ == "__main__":
    # Example with many different colors
    extensive_colors = StatusColorHelper.generate_status_colors(
        EStatus,
        StatusColorHelper.create_mapping(
            green=["active", "completed"],
            orange=["pending", "warning"],
            red=["cancelled", "expired"],
            gray=["inactive", "archived"],
            teal=["info"],
            cyan=["debug"],
            purple=["draft"],
            blue_gray=["archived"]  # Override gray for archived
        )
    )
    print("Extensive colors:", extensive_colors)
    
    # More specific example
    specific_colors = StatusColorHelper.generate_status_colors(
        EStatus,
        {
            "light_green": ["active"],
            "deep_orange": ["pending"],
            "indigo": ["completed"],
            "pink": ["cancelled"],
            "blue_gray": ["inactive"],
            "amber": ["warning"],
            "light_blue": ["info"],
            "brown": ["archived"]
        }
    )
    print("Specific colors:", specific_colors)