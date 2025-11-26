"""
Comprehensive TUI integration check - verifies descriptions and fields.
"""
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

def check_tui_definitions():
    """Check that all plugins have descriptions and fields in cli_tui.py"""
    print("=" * 80)
    print("TUI DEFINITIONS VERIFICATION")
    print("=" * 80)
    print()
    
    # Expected plugins
    plugins = [
        'AHB_M', 'AHB_S', 'basicAssertion', 'clockDivider', 'clockGate',
        'counter', 'hact', 'handshake', 'hbp', 'hfp', 'hsw', 'pulseWidth',
        'synchronizer', 'vact', 'vbp', 'vfp', 'videosyncall', 'vsw'
    ]
    
    cli_tui_path = scripts_dir / "cli_tui.py"
    content = cli_tui_path.read_text(encoding='utf-8')
    
    # Find descriptions section
    desc_start = content.find("def _get_plugin_description")
    desc_end = content.find("def ", desc_start + 1)
    desc_section = content[desc_start:desc_end]
    
    # Find fields section
    fields_start = content.find("def _get_plugin_fields")
    fields_end = content.find("return fields.get(plugin_name", fields_start)
    fields_section = content[fields_start:fields_end + 100]
    
    print("Checking descriptions...")
    missing_desc = []
    for plugin in plugins:
        if f"'{plugin}':" in desc_section or f'"{plugin}":' in desc_section:
            print(f"  ✓ {plugin}")
        else:
            print(f"  ✗ {plugin} - MISSING")
            missing_desc.append(plugin)
    
    print()
    print("Checking field definitions...")
    missing_fields = []
    for plugin in plugins:
        if f"'{plugin}':" in fields_section or f'"{plugin}":' in fields_section:
            print(f"  ✓ {plugin}")
        else:
            print(f"  ✗ {plugin} - MISSING")
            missing_fields.append(plugin)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if not missing_desc and not missing_fields:
        print("✓ SUCCESS: All 18 plugins have complete TUI integration!")
        print("  - All descriptions defined")
        print("  - All field definitions defined")
        return True
    else:
        print("✗ ISSUES FOUND:")
        if missing_desc:
            print(f"  Missing descriptions: {', '.join(missing_desc)}")
        if missing_fields:
            print(f"  Missing field definitions: {', '.join(missing_fields)}")
        return False

if __name__ == "__main__":
    success = check_tui_definitions()
    sys.exit(0 if success else 1)
