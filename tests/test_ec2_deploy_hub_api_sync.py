from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "ops" / "ec2" / "deploy-current.sh"
SERVICE = ROOT / "ops" / "ec2" / "hub-api.service"


def test_deploy_syncs_hub_api_launcher_into_shared_bin():
    text = DEPLOY.read_text(encoding="utf-8")

    assert '"$APP_ROOT/shared/bin"' in text
    assert "[deploy] Verifying hub-api launcher source" in text
    assert 'if [ ! -f "$RELEASE_DIR/ops/ec2/hub-api.sh" ]; then' in text
    assert "[deploy:error] Missing hub-api launcher source" in text
    assert "[deploy] Syncing hub-api launcher" in text
    assert 'install -m 0755 "$APP_ROOT/current/ops/ec2/hub-api.sh" "$APP_ROOT/shared/bin/hub-api"' in text


def test_deploy_syncs_launcher_after_current_symlink_switch():
    text = DEPLOY.read_text(encoding="utf-8")

    verify_source = text.index('if [ ! -f "$RELEASE_DIR/ops/ec2/hub-api.sh" ]; then')
    switch_current = text.index('echo "[deploy] Switching current symlink"')
    move_current = text.index('mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"')
    install_launcher = text.index('install -m 0755 "$APP_ROOT/current/ops/ec2/hub-api.sh" "$APP_ROOT/shared/bin/hub-api"')

    assert verify_source < switch_current
    assert move_current < install_launcher


def test_systemd_execstart_uses_synced_shared_launcher():
    text = SERVICE.read_text(encoding="utf-8")

    assert "ExecStart=/opt/hub-optimus/shared/bin/hub-api" in text
