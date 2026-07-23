#!/usr/bin/env python3
"""Manual MCP JSON-RPC client over SSH stdio to CoplayDev mcp-for-unity server (PC).
Usage:
  python3 /tmp/unity_mcp_call.py                      # tools/list -> names + brief
  python3 /tmp/unity_mcp_call.py <tool> '<json-args>' # tools/call
"""
import json, subprocess, sys, time

CMD = ["ssh", "-i", "/home/admin/.ssh/hermes-gpu", "-p", "2222", "haohaijiao@localhost",
       (r"C:\Users\haohaijiao\AppData\Local\hermes\bin\uvx.exe "
        r"--python C:\Users\haohaijiao\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe "
        r"--from mcpforunityserver mcp-for-unity --transport stdio")]

def rpc_lines(msgs):
    return "".join(json.dumps(m) + "\n" for m in msgs)

def main():
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05",
                       "capabilities": {},
                       "clientInfo": {"name": "hermes-manual", "version": "1.0"}}}
    inited = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    if len(sys.argv) >= 2:
        tool = sys.argv[1]
        args = json.loads(sys.argv[2]) if len(sys.argv) >= 3 else {}
        call = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": tool, "arguments": args}}
    else:
        call = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    p = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)

    def send(msg):
        p.stdin.write((json.dumps(msg) + "\n").encode())
        p.stdin.flush()

    def read_until(rpc_id, timeout=120):
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = p.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            line = line.decode("utf-8", errors="replace").strip()
            if not line.startswith("{"):
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == rpc_id:
                return msg
        return None

    send(init)
    if read_until(1, 60) is None:
        print("NO INIT RESPONSE")
        p.kill()
        return
    send(inited)
    send(call)
    msg = read_until(2, 120)
    p.kill()
    if msg is None:
        print("NO RESPONSE (id=2)")
        return
    res = msg.get("result", msg.get("error"))
    if isinstance(res, dict) and "tools" in res:
        tools = res["tools"]
        print(f"TOOLS: {len(tools)}")
        for t in tools:
            desc = (t.get("description") or "").split("\n")[0][:100]
            print(f"- {t['name']}: {desc}")
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2)[:6000])

if __name__ == "__main__":
    main()
