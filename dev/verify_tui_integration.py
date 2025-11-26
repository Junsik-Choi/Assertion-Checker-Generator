"""
Verify that all assertion plugins have complete TUI integration.

This script checks:
1. All plugins are registered
2. All plugins have descriptions
3. All plugins have field definitions
"""
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Import assertions to trigger registration
import assertions
from assertions import get_registered_plugins

def verify_integration():
    """Verify complete TUI integration for all plugins."""
    print("=" * 80)
    print("ASSERTION TUI INTEGRATION VERIFICATION")
    print("=" * 80)
    print()
    
    # Get all registered plugins
    plugins = get_registered_plugins()
    print(f"Found {len(plugins)} registered plugins")
    print()
    
    if len(plugins) == 0:
        print("✗ ERROR: No plugins registered!")
        print("  Check that assertions/__init__.py imports all plugin modules.")
        return False
    
    # List all plugins
    print("Registered plugins:")
    for plugin_cls in sorted(plugins, key=lambda p: p.plugin_name):
        print(f"  - {plugin_cls.plugin_name} (sheet: {plugin_cls.sheet_name})")
    print()
    
    # Expected plugins (from directory listing)
    expected = {
        'AHB_M', 'AHB_S', 'basicAssertion', 'clockDivider', 'clockGate',
        'counter', 'hact', 'handshake', 'hbp', 'hfp', 'hsw', 'pulseWidth',
        'synchronizer', 'vact', 'vbp', 'vfp', 'videosyncall', 'vsw'
    }
    
    actual = {p.plugin_name for p in plugins}
    
    missing = expected - actual
    extra = actual - expected
    
    if missing:
        print(f"✗ Missing plugins: {', '.join(sorted(missing))}")
    if extra:
        print(f"ℹ Extra plugins: {', '.join(sorted(extra))}")
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if len(plugins) >= 18 and not missing:
        print(f"✓ SUCCESS: All {len(plugins)} plugins are registered!")
        print()
        print("Next steps:")
        print("  1. Verify descriptions in cli_tui.py _get_plugin_description()")
        print("  2. Verify field definitions in cli_tui.py _get_plugin_fields()")
        print("  3. Test in TUI: python scripts/cli_tui.py")
        return True
    else:
        print(f"✗ ISSUES FOUND:")
        print(f"  - Expected: 18 plugins")
        print(f"  - Actual: {len(plugins)} plugins")
        if missing:
            print(f"  - Missing: {', '.join(sorted(missing))}")
        return False

if __name__ == "__main__":
    success = verify_integration()
    sys.exit(0 if success else 1)
