css_path = "frontend/src/styles.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# Replace earlier user-avatar blocks
old_1212 = '''.user-avatar {
  align-items: center !important;
  background: var(--sky) !important;
  border-radius: 50% !important;
  box-shadow: 0 0 0 1px rgba(20, 108, 206, 0.15) !important;
  box-sizing: border-box !important;
  color: var(--blue) !important;
  display: inline-flex !important;
  flex: 0 0 34px !important;
  flex-shrink: 0 !important;
  font-size: .72rem !important;
  font-weight: 800 !important;
  height: 34px !important;
  justify-content: center !important;
  line-height: 1 !important;
  margin: 0 !important;
  max-width: 34px !important;
  min-width: 34px !important;
  overflow: visible !important;
  padding: 0 !important;
  text-align: center !important;
  user-select: none;
  white-space: nowrap !important;
  width: 34px !important;
}'''

new_1212 = '''.user-avatar {
  display: inline-grid !important;
  place-items: center !important;
  align-items: center !important;
  justify-content: center !important;
  background: var(--sky) !important;
  border-radius: 50% !important;
  box-shadow: 0 0 0 1px rgba(20, 108, 206, 0.15) !important;
  box-sizing: border-box !important;
  color: var(--blue) !important;
  flex: 0 0 34px !important;
  flex-shrink: 0 !important;
  font-size: .72rem !important;
  font-weight: 800 !important;
  height: 34px !important;
  width: 34px !important;
  min-width: 34px !important;
  max-width: 34px !important;
  min-height: 34px !important;
  max-height: 34px !important;
  line-height: 1 !important;
  letter-spacing: 0 !important;
  text-indent: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  text-align: center !important;
  user-select: none;
  white-space: nowrap !important;
}'''

old_1700 = '''.user-avatar { 
  align-items: center !important; 
  background: var(--sky) !important; 
  border-radius: 50% !important; 
  box-shadow: 0 0 0 1px rgba(20, 108, 206, 0.15) !important;
  box-sizing: border-box !important;
  color: var(--blue) !important; 
  display: inline-flex !important; 
  flex: 0 0 34px !important; 
  flex-shrink: 0 !important;
  font-size: .72rem !important; 
  font-weight: 800 !important; 
  height: 34px !important; 
  justify-content: center !important; 
  line-height: 1 !important;
  margin: 0 !important;
  max-width: 34px !important;
  min-width: 34px !important;
  padding: 0 !important;
  text-align: center !important;
  user-select: none;
  white-space: nowrap !important;
  width: 34px !important; 
}'''

new_1700 = '''.user-avatar { 
  display: inline-grid !important;
  place-items: center !important;
  align-items: center !important; 
  justify-content: center !important; 
  background: var(--sky) !important; 
  border-radius: 50% !important; 
  box-shadow: 0 0 0 1px rgba(20, 108, 206, 0.15) !important;
  box-sizing: border-box !important;
  color: var(--blue) !important; 
  flex: 0 0 34px !important; 
  flex-shrink: 0 !important;
  font-size: .72rem !important; 
  font-weight: 800 !important; 
  height: 34px !important; 
  width: 34px !important; 
  min-width: 34px !important;
  max-width: 34px !important;
  min-height: 34px !important;
  max-height: 34px !important;
  line-height: 1 !important;
  letter-spacing: 0 !important;
  text-indent: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  text-align: center !important;
  user-select: none;
  white-space: nowrap !important;
}'''

if old_1212 in css:
    css = css.replace(old_1212, new_1212)
    print("Replaced 1212")
if old_1700 in css:
    css = css.replace(old_1700, new_1700)
    print("Replaced 1700")

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)
print("Updated avatar rules")
