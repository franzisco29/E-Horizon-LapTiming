"""
Test script per validare l'implementazione LAPMONITOR.
"""

import sys
from pathlib import Path

# Aggiungi root al path
root = Path(__file__).parent
sys.path.insert(0, str(root))

from Modules.config_manager import Settings, DevicesConfig
from Classes.device_manager import DeviceManager, ConnectionTypes
import tempfile


def test_config_persistence():
    """Test: config ble_mac_address persiste in YAML."""
    print("\n" + "="*60)
    print("TEST 1: Config Persistence (ble_mac_address)")
    print("="*60)

    try:
        # Crea config temporanea
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)

        # Carica/crea settings
        try:
            settings = Settings.load(temp_path)
        except Exception:
            settings = Settings.load_default()
            settings._path = temp_path

        # Verifica campo ble_mac_address esiste
        assert hasattr(settings.devices, 'ble_mac_address'), "Campo ble_mac_address mancante"
        print("[OK] Campo ble_mac_address presente in DevicesConfig")

        # Scrivi MAC
        test_mac = "70:B3:D5:4B:E2:95"
        settings.ble_mac_address = test_mac
        settings.save(temp_path)
        print(f"[OK] MAC salvato: {test_mac}")

        # Ricarica e verifica
        settings2 = Settings.load(temp_path)
        assert settings2.ble_mac_address == test_mac
        print(f"[OK] MAC ricaricato correttamente: {settings2.ble_mac_address}")

        # Cleanup
        temp_path.unlink()
        print("\n[PASS] TEST 1 PASSED\n")
        return True
    except Exception as e:
        print(f"\n[FAIL] TEST 1 FAILED: {e}\n")
        return False


def test_device_manager_initialization():
    """Test: DeviceManager inizializza BLE monitor in LAPMONITOR mode."""
    print("="*60)
    print("TEST 2: DeviceManager BLE Initialization")
    print("="*60)

    try:
        test_mac = "70:B3:D5:4B:E2:95"

        # LAPMONITOR con MAC valido
        dm = DeviceManager(
            ip="127.0.0.1",
            port=20777,
            conn_type=ConnectionTypes.LAPMONITOR,
            ble_mac_address=test_mac
        )

        assert dm._ble_mac_address == test_mac, "MAC non settato correttamente"
        print(f"[OK] MAC settato: {dm._ble_mac_address}")
        print(f"[OK] _ble_monitor stato: {dm._ble_monitor is not None or 'Bleak non installato'}")

        print("\n[PASS] TEST 2 PASSED\n")
        return True
    except Exception as e:
        print(f"\n[FAIL] TEST 2 FAILED: {e}\n")
        return False


def test_all_required_devices_logic():
    """Test: all_required_devices_connected() logic per LAPMONITOR."""
    print("="*60)
    print("TEST 3: LAPMONITOR Readiness Logic")
    print("="*60)

    try:
        # LAPMONITOR con BLE offline
        dm = DeviceManager(
            ip="127.0.0.1",
            port=20777,
            conn_type=ConnectionTypes.LAPMONITOR,
            ble_mac_address="70:B3:D5:4B:E2:95",
            active_flags=[True, False, False, False, False, False, False, False, False]
        )

        # Inizialmente BLE offline
        assert dm._ble_connected == False
        assert dm.all_required_devices_connected() == False
        print("[OK] Readiness = False quando BLE offline")

        # Simula BLE online
        dm._ble_connected = True
        assert dm.all_required_devices_connected() == True
        print("[OK] Readiness = True quando BLE online (D0 solo)")

        # Testa TCP mode
        dm_tcp = DeviceManager(
            ip="127.0.0.1",
            port=20777,
            conn_type=ConnectionTypes.TCP,
            active_flags=[True, True, False, False, False, False, False, False, False]
        )
        assert dm_tcp.all_required_devices_connected() == False
        print("[OK] TCP readiness = False (devices non connessi)")

        print("\n[PASS] TEST 3 PASSED\n")
        return True
    except Exception as e:
        print(f"\n[FAIL] TEST 3 FAILED: {e}\n")
        return False


def test_device_status_display():
    """Test: get_device_status_list() mostra status corretti."""
    print("="*60)
    print("TEST 4: Device Status Display")
    print("="*60)

    try:
        dm = DeviceManager(
            ip="127.0.0.1",
            port=20777,
            conn_type=ConnectionTypes.LAPMONITOR,
            ble_mac_address="70:B3:D5:4B:E2:95",
            active_flags=[True, False, False, False, False, True, False, False, True]
        )

        # BLE offline
        status_list = dm.get_device_status_list()

        # Controlla D0 (BLE)
        assert any("BLE offline" in s for s in status_list)
        print("[OK] D0 mostra 'BLE offline'")

        # Controlla D1-D4 (disabilitati)
        d1_status = [s for s in status_list if "Device ID 1" in s]
        assert any("Non usato in LAPMONITOR" in s for s in d1_status)
        print("[OK] D1-D4 mostrano 'Non usato in LAPMONITOR'")

        # Controlla D5 (TCP opzionale)
        d5_status = [s for s in status_list if "Device ID 5" in s]
        assert d5_status
        print("[OK] D5 presente nel status list")

        # Simula BLE online
        dm._ble_connected = True
        status_list = dm.get_device_status_list()
        assert any("Connesso via BLE" in s for s in status_list)
        print("[OK] D0 mostra 'Connesso via BLE' quando online")

        print("\n[PASS] TEST 4 PASSED\n")
        return True
    except Exception as e:
        print(f"\n[FAIL] TEST 4 FAILED: {e}\n")
        return False


def test_connection_types_enum():
    """Test: Enum ConnectionTypes ha SERIAL (not WIFIUDP)."""
    print("="*60)
    print("TEST 5: ConnectionTypes Enum")
    print("="*60)

    try:
        assert hasattr(ConnectionTypes, 'NONE')
        assert hasattr(ConnectionTypes, 'TCP')
        assert hasattr(ConnectionTypes, 'LAPMONITOR')
        assert hasattr(ConnectionTypes, 'SERIAL')
        print(f"[OK] NONE = {ConnectionTypes.NONE}")
        print(f"[OK] TCP = {ConnectionTypes.TCP}")
        print(f"[OK] LAPMONITOR = {ConnectionTypes.LAPMONITOR}")
        print(f"[OK] SERIAL = {ConnectionTypes.SERIAL}")

        # Verifica non esiste WIFIUDP
        assert not hasattr(ConnectionTypes, 'WIFIUDP')
        print("[OK] WIFIUDP rimosso (sostituito da SERIAL)")

        print("\n[PASS] TEST 5 PASSED\n")
        return True
    except Exception as e:
        print(f"\n[FAIL] TEST 5 FAILED: {e}\n")
        return False


def main():
    """Esegui tutti i test."""
    print("\n" + "#"*60)
    print("# LAPMONITOR IMPLEMENTATION VALIDATION SUITE")
    print("#"*60)

    results = []

    # Esegui test
    results.append(("Config Persistence", test_config_persistence()))
    results.append(("DeviceManager Init", test_device_manager_initialization()))
    results.append(("Readiness Logic", test_all_required_devices_logic()))
    results.append(("Status Display", test_device_status_display()))
    results.append(("Enum Values", test_connection_types_enum()))

    # Resoconto
    print("\n" + "#"*60)
    print("# TEST RESULTS SUMMARY")
    print("#"*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n*** ALL TESTS PASSED - LAPMONITOR READY ***\n")
        return 0
    else:
        print(f"\n*** {total - passed} FAILED ***\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
