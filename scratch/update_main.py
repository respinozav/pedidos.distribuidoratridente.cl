import re

# 1. Update frontend/src/main.jsx
main_path = "frontend/src/main.jsx"
with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

# Trim initials for user-avatar in user list
content = content.replace(
    '<span className="user-avatar">{item.nombre.slice(0, 2).toUpperCase()}</span>',
    '<span className="user-avatar">{(item.nombre || "US").trim().slice(0, 2).toUpperCase()}</span>'
)

# Insert customer-bottom-bar before </main> in Shop component
target = '''            </section>
          )}
        </div>
      </section>
    </main>'''

replacement = '''            </section>
          )}
        </div>
      </section>
      <nav className="customer-bottom-bar" aria-label="Navegación móvil">
        <button
          type="button"
          className={`customer-bottom-tab ${section === "create" && !cartDrawerOpen ? "active" : ""}`}
          onClick={() => {
            setSection("create");
            setCartDrawerOpen(false);
            setError("");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        >
          <ShoppingBag size={20} />
          <span>Comprar</span>
        </button>
        <button
          type="button"
          className={`customer-bottom-tab ${section === "history" ? "active" : ""}`}
          onClick={() => {
            openHistory();
            setCartDrawerOpen(false);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        >
          <ClipboardList size={20} />
          <span>Pedidos</span>
        </button>
        <button
          type="button"
          className={`customer-bottom-tab cart-tab ${cartDrawerOpen ? "active" : ""}`}
          onClick={() => setCartDrawerOpen((prev) => !prev)}
          aria-label={`Ver pedido actual con ${totalItems} productos`}
        >
          <div className="bottom-cart-icon-wrap">
            <ShoppingBag size={21} />
            {totalItems > 0 && <span className="bottom-cart-badge">{totalItems}</span>}
          </div>
          <span>Mi Pedido</span>
        </button>
        <button
          type="button"
          className={`customer-bottom-tab ${section === "profile" ? "active" : ""}`}
          onClick={() => {
            setSection("profile");
            setCartDrawerOpen(false);
            setError("");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        >
          <User size={20} />
          <span>Mi Cuenta</span>
        </button>
        <button
          type="button"
          className={`customer-bottom-tab ${section === "faq" ? "active" : ""}`}
          onClick={() => {
            setSection("faq");
            setCartDrawerOpen(false);
            setError("");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        >
          <HelpCircle size={20} />
          <span>Ayuda</span>
        </button>
      </nav>
    </main>'''

if target in content:
    content = content.replace(target, replacement)
    print("Successfully inserted customer-bottom-bar into Shop in main.jsx")
else:
    print("WARNING: target not found in main.jsx")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(content)
