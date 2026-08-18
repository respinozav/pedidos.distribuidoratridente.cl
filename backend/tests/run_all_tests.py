import tests.test_catalog as tc
import tests.test_ordering as to
import tests.test_notifications as tn


class MonkeyPatch:
    def setattr(self, *args):
        if len(args) == 2:
            target, value = args
            parts = target.rsplit(".", 1)
            mod = __import__(parts[0], fromlist=[parts[1]])
            setattr(mod, parts[1], value)
        elif len(args) == 3:
            target, name, value = args
            setattr(target, name, value)


def main():
    mp = MonkeyPatch()
    tc.test_build_full_catalog_pdf_returns_valid_pdf()
    tc.test_build_public_vs_full_catalog_cache_and_invalidation()
    to.test_create_creates_default_state_when_none_exists(mp)
    tn.test_product_detail_label_compacts_code_on_same_line()
    tn.test_order_pdf_contains_valid_header()
    tn.test_notify_administrators_only_sends_to_recibe_pedido_users(mp)
    print(">>> ALL 6 UNIT TESTS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    main()
