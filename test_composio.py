"""Test Composio import"""
try:
    from composio_core import ComposioToolSet
    print("✅ Composio encontrado como composio_core")
except ImportError:
    try:
        from composio import ComposioToolSet
        print("✅ Composio encontrado como composio")
    except ImportError as e:
        print(f"❌ Composio no encontrado: {e}")

