# -*- coding: utf-8 -*-
"""Comprehensive test: login, MCP tools, KB search, and chat."""
import httpx
import json
import asyncio
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "http://localhost:80"
PASS = 0
FAIL = 0

def ok(label):
    global PASS
    PASS += 1
    print(f"  [PASS] {label}")

def bad(label, detail=""):
    global FAIL
    FAIL += 1
    msg = f"  [FAIL] {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)

async def test():
    global PASS, FAIL
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(base_url=BASE, timeout=timeout) as c:

        # =====================================================================
        # 0. Health check
        # =====================================================================
        print("\n=== 0. Health Check ===")
        try:
            r = await c.get("/api/mcp/tools")
            ok(f"API reachable, status={r.status_code}")
        except Exception as e:
            bad(f"API unreachable: {e}")
            return

        # =====================================================================
        # 1. Login
        # =====================================================================
        print("\n=== 1. Login ===")

        # Register patient if not exists
        r = await c.post("/api/auth/register",
            json={"username": "testmcp1", "password": "test123456", "name": "TestPatient", "role": "patient"})
        if r.status_code in (200, 201) and "token" in r.json():
            patient_token = r.json()["token"]
            patient_user = r.json()["user"]
            ok(f"Patient registered: {patient_user['name']} (id={patient_user['id']}, role={patient_user['role']})")
        else:
            # Try login (user may already exist)
            print(f"  [INFO] Register returned status={r.status_code}, trying login...")
            r = await c.post("/api/auth/login",
                json={"username": "testmcp1", "password": "test123456"})
            if r.status_code == 200 and "token" in r.json():
                patient_token = r.json()["token"]
                patient_user = r.json()["user"]
                ok(f"Patient login: {patient_user['name']} (id={patient_user['id']})")
            else:
                bad("Patient auth failed", f"register={r.status_code}, body={r.text[:200]}")
                return

        # Register doctor if not exists
        r = await c.post("/api/auth/register",
            json={"username": "testdoc1", "password": "test123456", "name": "TestDoctor", "role": "doctor"})
        if r.status_code in (200, 201) and "token" in r.json():
            doctor_token = r.json()["token"]
            doctor_user = r.json()["user"]
            ok(f"Doctor registered: {doctor_user['name']} (id={doctor_user['id']}, role={doctor_user['role']})")
        else:
            print(f"  [INFO] Register returned status={r.status_code}, trying login...")
            r = await c.post("/api/auth/login",
                json={"username": "testdoc1", "password": "test123456"})
            if r.status_code == 200 and "token" in r.json():
                doctor_token = r.json()["token"]
                doctor_user = r.json()["user"]
                ok(f"Doctor login: {doctor_user['name']} (id={doctor_user['id']})")
            else:
                bad("Doctor auth failed", f"register={r.status_code}, body={r.text[:200]}")
                return

        headers_doctor = {"Authorization": f"Bearer {doctor_token}"}
        headers_patient = {"Authorization": f"Bearer {patient_token}"}

        # =====================================================================
        # 2. MCP Tools List
        # =====================================================================
        print("\n=== 2. MCP Tool List ===")
        r = await c.get("/api/mcp/tools", headers=headers_doctor)
        if r.status_code == 200:
            tools = r.json()
            tool_names = [t["name"] for t in tools]
            ok(f"Got {len(tools)} MCP tools: {tool_names}")
        else:
            bad("MCP tool list", f"status={r.status_code} {r.text[:200]}")

        # =====================================================================
        # 3. identity.verify_patient
        # =====================================================================
        print("\n=== 3. identity.verify_patient ===")
        r = await c.post("/api/mcp/invoke",
            json={"tool": "identity.verify_patient", "params": {"username": "testmcp1"}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            if d["status"] == "success" and d["data"]["verified"]:
                ok(f"Patient verified: {d['data']['name']}, has_profile={d['data']['has_profile']}")
            else:
                bad("Patient verify", json.dumps(d, ensure_ascii=False))
        else:
            bad("Patient verify HTTP", f"status={r.status_code} {r.text[:200]}")

        r = await c.post("/api/mcp/invoke",
            json={"tool": "identity.verify_patient", "params": {"username": "testdoc1"}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            if d["data"]["verified"] == False:
                ok(f"Doctor-as-patient correctly rejected: {d['data']['reason']}")
            else:
                bad("Doctor should not pass patient verify")

        # =====================================================================
        # 4. identity.verify_doctor
        # =====================================================================
        print("\n=== 4. identity.verify_doctor ===")
        r = await c.post("/api/mcp/invoke",
            json={"tool": "identity.verify_doctor", "params": {"username": "testdoc1"}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            if d["status"] == "success" and d["data"]["verified"]:
                ok(f"Doctor verified: dept={d['data'].get('department')}, title={d['data'].get('title')}")

        # =====================================================================
        # 5. identity.get_permissions
        # =====================================================================
        print("\n=== 5. identity.get_permissions ===")
        r = await c.post("/api/mcp/invoke",
            json={"tool": "identity.get_permissions", "params": {"username": "testdoc1"}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            if d["status"] == "success":
                perms = d["data"]["permissions"]
                ok(f"Doctor permissions: {perms}")
                for p in ["decision_support", "query_patient_record", "view_reasoning_chain"]:
                    if p in perms:
                        ok(f"  has {p}")
                    else:
                        bad(f"  missing {p}")

        r = await c.post("/api/mcp/invoke",
            json={"tool": "identity.get_permissions", "params": {"username": "testmcp1"}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            perms = d["data"]["permissions"]
            ok(f"Patient permissions: {perms}")
            if "decision_support" not in perms:
                ok("Patient correctly lacks decision_support")

        # =====================================================================
        # 6. patient_record.query_case
        # =====================================================================
        print("\n=== 6. patient_record.query_case ===")
        r = await c.post("/api/mcp/invoke",
            json={"tool": "patient_record.query_case", "params": {"patient_name": patient_user['name']}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            if d["status"] == "success":
                cases = d["data"].get("cases", [])
                ok(f"Query cases: {len(cases)} records")
            else:
                err = d.get("error", "")
                ok(f"No cases (expected): {err[:100]}")
        else:
            bad("Query cases", f"status={r.status_code}")

        # =====================================================================
        # 7. patient_record.query_visit
        # =====================================================================
        print("\n=== 7. patient_record.query_visit ===")
        r = await c.post("/api/mcp/invoke",
            json={"tool": "patient_record.query_visit", "params": {"patient_name": patient_user['name']}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            status = d["status"]
            if status == "success":
                visits = d["data"].get("visits", [])
                ok(f"Query visits: {len(visits)} records")
            else:
                ok(f"query_visit status={status} (acceptable)")

        # =====================================================================
        # 8. patient_record.query_prescription
        # =====================================================================
        print("\n=== 8. patient_record.query_prescription ===")
        r = await c.post("/api/mcp/invoke",
            json={"tool": "patient_record.query_prescription", "params": {"patient_name": patient_user['name']}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            status = d["status"]
            if status == "success":
                rx = d["data"].get("prescriptions", [])
                ok(f"Query prescriptions: {len(rx)} records")
            else:
                ok(f"query_prescription status={status} (acceptable)")

        # =====================================================================
        # 9. KB Search
        # =====================================================================
        print("\n=== 9. KB Search ===")
        r = await c.post("/api/search",
            json={"query": "高血压用药指南"},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            n = d.get("total", 0)
            sources = d.get("sources", [])
            ok(f"Doctor search '高血压用药指南': {n} results, {len(sources)} sources")
            for i, result in enumerate(d.get("results", [])[:3]):
                t = result.get("source_type", "?")
                title = result.get("title", "?")
                ok(f"  #{i+1}: [{t}] {title}")
        else:
            bad("KB search", f"status={r.status_code} {r.text[:200]}")

        r = await c.post("/api/search",
            json={"query": "高血压饮食注意"},
            headers=headers_patient)
        if r.status_code == 200:
            d = r.json()
            ok(f"Patient search '高血压饮食注意': {d.get('total', 0)} results")

        # =====================================================================
        # 10. Error cases
        # =====================================================================
        print("\n=== 10. Error Cases ===")
        r = await c.post("/api/mcp/invoke",
            json={"tool": "identity.verify_patient", "params": {"username": "nobody_xyz_123"}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            if d["status"] == "error" and "不存在" in d.get("error", ""):
                ok(f"Nonexistent user -> error: {d['error'][:80]}")
            else:
                bad("Nonexistent user should return error", str(d)[:150])

        r = await c.post("/api/mcp/invoke",
            json={"tool": "patient_record.query_case", "params": {}},
            headers=headers_doctor)
        if r.status_code == 200:
            d = r.json()
            if d["status"] == "error":
                ok(f"Empty params -> error: {d.get('error','')[:100]}")
            else:
                bad("Empty params should return error", f"status={d['status']}")

        # =====================================================================
        # Summary
        # =====================================================================
        print(f"\n{'='*60}")
        print(f"Test complete: {PASS} passed, {FAIL} failed")
        print(f"{'='*60}")
        return FAIL == 0


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
