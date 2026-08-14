import argparse
import asyncio
import hashlib
import hmac
import os
import socket
from pathlib import Path

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
ADVERTISING_UUID = "0000a15a-0000-1000-8000-00805f9b34fb"
STATES = ("idle", "thinking", "running", "approval", "success", "error")
SOCKET_PATH = Path(os.environ.get("FLIPPER_STATE_SOCKET", "/tmp/flipper-state.sock"))
TCP_HOST = os.environ.get("FLIPPER_STATE_HOST", "127.0.0.1")
TCP_PORT = int(os.environ.get("FLIPPER_STATE_PORT", "39871"))
CACHE_PATH = Path(os.environ.get("FLIPPER_STATE_DEVICE_CACHE", "~/.flipper-state-device")).expanduser()
KEY_PATH = Path(os.environ.get("FLIPPER_STATE_KEY", "~/.flipper-pet/device.key")).expanduser()


async def find_flipper(timeout: float):
    cached = CACHE_PATH.read_text().strip() if CACHE_PATH.exists() else ""
    if cached:
        try:
            device = await BleakScanner.find_device_by_address(cached, timeout=min(timeout, 8))
            if device is not None:
                print(f"Using cached Flipper {cached}…", flush=True)
                return device
        except (BleakError, OSError):
            CACHE_PATH.unlink(missing_ok=True)
    print("Scanning for AI Pet…", flush=True)
    device = await BleakScanner.find_device_by_filter(
        lambda device, advertisement: (
            (advertisement.local_name or "").startswith(("AIPet", "AIState"))
            or ADVERTISING_UUID in [uuid.lower() for uuid in advertisement.service_uuids]
        ),
        timeout=timeout,
    )
    if device is None:
        raise RuntimeError(
            "AI Pet was not found. Open the AI Pet app on Flipper and keep it nearby."
        )
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(device.address)
    return device


async def run_daemon(timeout: float) -> None:
    if not KEY_PATH.is_file() or len(KEY_PATH.read_bytes()) != 32:
        raise RuntimeError("电脑尚未绑定 AI Pet；请先在 Web 页面点击“绑定电脑”")
    key = KEY_PATH.read_bytes()
    device = await find_flipper(timeout)
    if os.name == "nt":
        try:
            with socket.create_connection((TCP_HOST, TCP_PORT), timeout=0.2):
                raise RuntimeError("flipper-state daemon is already running")
        except OSError:
            pass
    elif SOCKET_PATH.exists():
        try:
            reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
            writer.close()
            await writer.wait_closed()
            raise RuntimeError("flipper-state daemon is already running")
        except (ConnectionRefusedError, FileNotFoundError):
            SOCKET_PATH.unlink(missing_ok=True)

    print(f"Connecting to {device.name or device.address}…", flush=True)
    async with BleakClient(device, timeout=timeout) as client:
        print("Connected. Local state socket is ready.", flush=True)
        challenge = asyncio.get_running_loop().create_future()
        authenticated = asyncio.get_running_loop().create_future()
        decisions: dict[str, asyncio.Future] = {}
        approval_lock = asyncio.Lock()

        def on_notify(_sender, data: bytearray):
            message = bytes(data).split(b"\0", 1)[0].decode(errors="replace").strip()
            if message.startswith("challenge ") and not challenge.done():
                challenge.set_result(message.split(" ", 1)[1])
            elif message == "auth ok" and not authenticated.done():
                authenticated.set_result(True)
            elif message == "auth failed" and not authenticated.done():
                authenticated.set_exception(RuntimeError("AI Pet 应用层认证失败"))
            elif message.startswith("decision "):
                parts = message.split()
                if len(parts) == 3 and parts[1] in decisions and not decisions[parts[1]].done():
                    decisions[parts[1]].set_result(parts[2])

        await client.start_notify(TX_UUID, on_notify)
        await client.write_gatt_char(RX_UUID, b"hello\n", response=True)
        challenge_hex = await asyncio.wait_for(challenge, timeout=timeout)
        digest = hmac.new(key, bytes.fromhex(challenge_hex), hashlib.sha256).hexdigest()[:32]
        await client.write_gatt_char(RX_UUID, f"auth {digest}\n".encode(), response=True)
        await asyncio.wait_for(authenticated, timeout=timeout)

        async def handle_command(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            raw = await reader.readline()
            command = raw.decode(errors="replace").strip()
            state = command.split()[1] if command.startswith("fx ") and len(command.split()) == 7 else command
            approval_parts = command.split(" ", 2) if command.startswith("approval_req ") else []
            handoff_parts = command.split() if command.startswith("approval_handoff ") else []
            if approval_parts and len(approval_parts) >= 2:
                request_id = approval_parts[1]
                if len(request_id) > 16 or len(command.encode()) > 63:
                    writer.write(b"error: invalid approval request\n")
                else:
                    async with approval_lock:
                        decision = asyncio.get_running_loop().create_future()
                        decisions[request_id] = decision
                        try:
                            await client.write_gatt_char(
                                RX_UUID, f"{command}\n".encode(), response=True
                            )
                            result = await decision
                            if result in ("allow", "deny"):
                                writer.write(f"decision: {request_id} {result}\n".encode())
                            else:
                                writer.write(f"cancelled: {request_id}\n".encode())
                        finally:
                            decisions.pop(request_id, None)
            elif len(handoff_parts) == 2 and len(handoff_parts[1]) <= 16:
                pending = decisions.get(handoff_parts[1])
                if pending is not None and not pending.done():
                    pending.set_result("cancel")
                await client.write_gatt_char(RX_UUID, f"{command}\n".encode(), response=True)
                writer.write(f"ok: approval_handoff {handoff_parts[1]}\n".encode())
            elif state not in STATES or len(command.encode()) > 63:
                writer.write(b"error: invalid command\n")
            elif not client.is_connected:
                writer.write(b"error: Flipper disconnected\n")
            else:
                try:
                    await client.write_gatt_char(
                        RX_UUID, f"{command}\n".encode(), response=True
                    )
                    writer.write(f"ok: {state}\n".encode())
                    print(f"State sent: {state}", flush=True)
                except Exception as error:
                    writer.write(f"error: {error}\n".encode())
            try:
                await writer.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            writer.close()
            await writer.wait_closed()

        if os.name == "nt":
            server = await asyncio.start_server(handle_command, TCP_HOST, TCP_PORT)
        else:
            server = await asyncio.start_unix_server(handle_command, path=SOCKET_PATH)
        try:
            while client.is_connected:
                await asyncio.sleep(0.5)
            raise RuntimeError("Flipper disconnected")
        finally:
            server.close()
            await server.wait_closed()
            SOCKET_PATH.unlink(missing_ok=True)


async def run_service(timeout: float, retry_delay: float) -> None:
    """Keep reconnecting so the BLE bridge can run as a login service."""
    while True:
        try:
            await run_daemon(timeout)
        except (BleakError, RuntimeError, TimeoutError, ValueError) as error:
            print(f"Disconnected: {error}. Retrying in {retry_delay:g}s…")
        await asyncio.sleep(retry_delay)

async def send_local_state(state: str) -> None:
    try:
        if os.name == "nt":
            reader, writer = await asyncio.open_connection(TCP_HOST, TCP_PORT)
        else:
            reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
    except (ConnectionRefusedError, FileNotFoundError) as error:
        raise RuntimeError(
            "daemon is not running; start it with: flipper-state daemon"
        ) from error
    writer.write(f"{state}\n".encode())
    await writer.drain()
    response = (await reader.readline()).decode().strip()
    writer.close()
    await writer.wait_closed()
    if not response.startswith("ok:"):
        raise RuntimeError(response or "daemon returned no response")
    print(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Control Flipper AI Pet over BLE")
    parser.add_argument("command", choices=(*STATES, "daemon", "service"))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retry-delay", type=float, default=5.0)
    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="silently succeed when the Flipper bridge is unavailable",
    )
    args = parser.parse_args()
    try:
        if args.command == "daemon":
            asyncio.run(run_daemon(args.timeout))
        elif args.command == "service":
            asyncio.run(run_service(args.timeout, args.retry_delay))
        else:
            asyncio.run(send_local_state(args.command))
    except (BleakError, RuntimeError, TimeoutError, ValueError) as error:
        if args.best_effort:
            return
        parser.exit(2, f"error: {error}\n")
    except (OSError, PermissionError) as error:
        if args.best_effort:
            return
        parser.exit(2, f"error: {error}\n")
