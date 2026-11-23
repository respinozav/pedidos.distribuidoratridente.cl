import re

css_path = "frontend/src/styles.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# 1. Replace the obsolete line 2759 media query for customer-sidebar
old_mq = '@media (max-width: 991px) { .customer-portal { display: block; height: auto; overflow: visible; } .customer-sidebar { flex: 0 0 auto; height: auto; min-height: auto; padding: .9rem 1rem; position: relative; width: 100%; } .customer-workspace { flex: 0 0 100%; height: auto; margin-left: 0; overflow: visible; width: 100%; } .customer-sidebar .customer-brand { padding: .35rem .25rem 1rem; } .customer-sidebar .customer-brand .brand-mark { display: none; } .customer-nav { align-items: center; grid-template-columns: repeat(3, minmax(0, 1fr)); padding-right: 46px; } .customer-nav-title { padding: .55rem .25rem; } .customer-nav button { justify-content: center; margin: 0; white-space: normal; } .customer-submenu { border-left: 0; display: contents; margin: 0; padding: 0; } .account-nav-title { border-top: 0; margin-top: 0; padding-top: .55rem; } .customer-profile { display: none; } .customer-sidebar .logout-button { align-items: center; bottom: .9rem; display: inline-flex; font-size: 0; height: 38px; justify-content: center; padding: .5rem; position: absolute; right: .85rem; width: 38px; } .customer-sidebar .logout-button svg { margin: 0; } }'

new_mq = '''@media (max-width: 991px) {
  .customer-portal {
    display: block !important;
    height: auto !important;
    min-height: 100vh;
    overflow-x: hidden;
  }
  .customer-sidebar {
    display: none !important;
  }
  .customer-workspace {
    flex: 0 0 100% !important;
    height: auto !important;
    margin-left: 0 !important;
    overflow: visible !important;
    width: 100% !important;
    padding-bottom: calc(78px + env(safe-area-inset-bottom, 0px)) !important;
  }
  .customer-portal-header {
    min-height: 56px !important;
    height: 56px !important;
    padding: 0 0.85rem !important;
    position: sticky !important;
    top: 0 !important;
    z-index: 1030 !important;
    background: #ffffff !important;
    border-bottom: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 4px rgba(16, 42, 67, 0.05) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
  }
  .customer-header-left {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }
  .customer-mobile-brand {
    display: flex !important;
    align-items: center;
    gap: 0.4rem;
  }
  .customer-mobile-brand .brand-mark {
    width: 28px;
    height: 28px;
    background: #102a43;
    color: #fca311;
    font-weight: 800;
    font-size: 0.72rem;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .customer-mobile-brand strong {
    font-size: 0.92rem;
    color: #102a43;
    font-weight: 800;
    letter-spacing: -0.01em;
  }
  .customer-portal-header h1 {
    font-size: 1rem !important;
    margin: 0 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .customer-header-right {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }
  .customer-header-logout-btn {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #64748b;
    padding: 0;
    transition: all 0.2s ease;
  }
  .customer-header-logout-btn:active {
    background: #fee2e2;
    color: #ef4444;
  }
}'''

if old_mq in css:
    css = css.replace(old_mq, new_mq)
    print("Replaced obsolete customer-sidebar media query")
else:
    print("WARNING: old_mq not found in styles.css")

# 2. Add or update bottom navigation bar styles and avatar centering
bottom_bar_css = '''
/* ==========================================================================
   MODERN ERP B2B: NATIVE MOBILE APP BOTTOM NAVIGATION BAR (CUSTOMER)
   ========================================================================== */
.customer-bottom-bar {
  display: none;
}

@media (max-width: 991px) {
  .customer-bottom-bar {
    display: flex !important;
    align-items: stretch;
    justify-content: space-around;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: calc(58px + env(safe-area-inset-bottom, 0px));
    padding-bottom: env(safe-area-inset-bottom, 0px);
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
    box-shadow: 0 -3px 12px rgba(16, 42, 67, 0.08);
    z-index: 1040;
    user-select: none;
  }

  .customer-bottom-tab {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    padding: 6px 4px;
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 0.68rem;
    font-weight: 600;
    text-align: center;
    transition: all 0.15s ease;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }

  .customer-bottom-tab svg {
    color: #64748b;
    transition: transform 0.15s ease, color 0.15s ease;
    flex-shrink: 0;
  }

  .customer-bottom-tab span {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    line-height: 1.1;
  }

  .customer-bottom-tab:active {
    transform: scale(0.95);
  }

  .customer-bottom-tab.active {
    color: #146cce;
    font-weight: 800;
  }

  .customer-bottom-tab.active svg {
    color: #146cce;
    transform: translateY(-1px);
  }

  .customer-bottom-tab.cart-tab {
    color: #102a43;
  }

  .bottom-cart-icon-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .bottom-cart-badge {
    position: absolute;
    top: -6px;
    right: -10px;
    min-width: 18px;
    height: 18px;
    padding: 0 4px;
    border-radius: 99px;
    background: #fca311;
    color: #102a43;
    font-size: 0.65rem;
    font-weight: 900;
    line-height: 18px;
    text-align: center;
    border: 2px solid #ffffff;
    box-shadow: 0 1px 4px rgba(252, 163, 17, 0.4);
  }
}
'''

# Update avatar centering rules to use inline-grid and place-items center
old_avatar_block = '''/* Unified Avatar Centering - Rock Solid in all Views */
.user-avatar,
.customer-profile > span,
.sidebar-user > span {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  vertical-align: middle !important;
  line-height: 1 !important;
  letter-spacing: normal !important;
  text-indent: 0 !important;
  font-size: .74rem !important;
  font-weight: 800 !important;
  user-select: none !important;
  box-sizing: border-box !important;
  flex-shrink: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

.user-avatar {
  background: var(--sky) !important;
  border-radius: 50% !important;
  box-shadow: 0 0 0 1px rgba(20, 108, 206, 0.15) !important;
  color: var(--blue) !important;
  height: 34px !important;
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
}'''

new_avatar_block = '''/* Unified Avatar Centering - Rock Solid in all Views */
.user-avatar,
.customer-profile > span,
.sidebar-user > span {
  display: inline-grid !important;
  place-items: center !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  vertical-align: middle !important;
  line-height: 1 !important;
  letter-spacing: 0 !important;
  text-indent: 0 !important;
  font-size: .74rem !important;
  font-weight: 800 !important;
  user-select: none !important;
  box-sizing: border-box !important;
  flex: 0 0 34px !important;
  flex-shrink: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  border-radius: 50% !important;
  overflow: hidden !important;
}

.user-avatar {
  background: var(--sky) !important;
  border-radius: 50% !important;
  box-shadow: 0 0 0 1px rgba(20, 108, 206, 0.15) !important;
  color: var(--blue) !important;
  height: 34px !important;
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
  min-height: 34px !important;
  max-height: 34px !important;
}'''

if old_avatar_block in css:
    css = css.replace(old_avatar_block, new_avatar_block)
    print("Updated avatar block with grid centering")
else:
    print("Note: old_avatar_block not found exactly, appending refined rules")
    css += "\n" + new_avatar_block

# Append bottom_bar_css
if ".customer-bottom-bar" not in css:
    css += "\n" + bottom_bar_css
    print("Appended bottom_bar_css")
else:
    print(".customer-bottom-bar already in CSS")

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)
print("CSS updated successfully")
