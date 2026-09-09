import tests.test_catalog as tc
import tests.test_ordering as to
import tests.test_notifications as tn
import tests.test_publicidad as tp
import tests.test_sesion_logs as ts
import tests.test_defontana as td
import tests.test_admin_profile as tap
import tests.test_colaborador_role as tcol
import tests.test_producto_notificar_stock as tpns
import tests.test_negative_stock_order as tnso
import tests.test_publicidad_email as tpe


class MonkeyPatch:
    def __init__(self):
        self._undo_stack = []

    def setattr(self, *args):
        if len(args) == 2:
            target, value = args
            parts = target.rsplit(".", 1)
            mod = __import__(parts[0], fromlist=[parts[1]])
            if hasattr(mod, parts[1]):
                orig = getattr(mod, parts[1])
                self._undo_stack.append((mod, parts[1], True, orig))
            else:
                self._undo_stack.append((mod, parts[1], False, None))
            setattr(mod, parts[1], value)
        elif len(args) == 3:
            target, name, value = args
            if hasattr(target, name):
                orig = getattr(target, name)
                self._undo_stack.append((target, name, True, orig))
            else:
                self._undo_stack.append((target, name, False, None))
            setattr(target, name, value)

    def undo(self):
        for obj, name, existed, orig in reversed(self._undo_stack):
            if existed:
                setattr(obj, name, orig)
            elif hasattr(obj, name):
                delattr(obj, name)
        self._undo_stack.clear()


def main():
    mp = MonkeyPatch()
    tc.test_build_full_catalog_pdf_returns_valid_pdf()
    tc.test_build_public_vs_full_catalog_cache_and_invalidation()
    try:
        to.test_create_creates_default_state_when_none_exists(mp)
    finally:
        mp.undo()
    tn.test_order_pdf_filename_generation()
    tn.test_product_detail_label_compacts_code_on_same_line()
    tn.test_order_pdf_contains_valid_header()
    tn.test_order_pdf_with_mixed_afecto_and_exento()
    try:
        tn.test_notify_administrators_only_sends_to_recibe_pedido_users(mp)
    finally:
        mp.undo()
    tp.test_publicidad_crud_cycle()
    ts.test_session_logs_recording_and_queries()
    td.test_defontana_save_order_mocked()
    td.test_defontana_item_packaging_rules()
    td.test_defontana_resolve_client_and_product()
    td.test_defontana_order_exclusively_afecto()
    td.test_defontana_order_exclusively_exento()
    td.test_defontana_order_mixed_afecto_and_exento()
    td.test_defontana_create_client_mocked()
    td.test_defontana_sync_order_creates_client_when_not_exists()
    tap.test_admin_profile_workflow()
    tcol.test_colaborador_role_permissions()
    tpns.test_product_input_validation()
    tpns.test_product_crud_stock_notification()
    tpns.test_stock_alert_query()
    tnso.test_negative_stock_cart_and_order()
    tpe.test_publicidad_email_dto()
    tpe.test_publicidad_html_builder()
    tpe.test_send_publicidad_campaign_isolated_bcc()
    print(">>> ALL 26 UNIT TESTS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    main()

