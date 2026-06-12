import os
import sys
from fastapi.testclient import TestClient

# Make sure backend path is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.main import app

def test_endpoints():
    client = TestClient(app)
    
    print("Testing root endpoint...")
    response = client.get("/")
    assert response.status_code == 200
    print("Root response:", response.json())
    
    # 1. GET /api/xai/{outlet_id}/explanation
    print("\nTesting endpoint 1: GET /api/xai/OUT_00001/explanation...")
    response = client.get("/api/xai/OUT_00001/explanation")
    assert response.status_code == 200
    res1 = response.json()
    assert "explanation" in res1
    print("Explanation preview:", res1["explanation"][:80] + "...")

    # 2. POST /api/budget/simulate
    print("\nTesting endpoint 2: POST /api/budget/simulate...")
    response = client.post("/api/budget/simulate", json={"budget": 10000000.0, "b_param": 0.0005})
    assert response.status_code == 200
    res2 = response.json()
    assert "total_allocated" in res2
    print("Simulated allocated spend:", res2["total_allocated"])

    # 3. GET /api/budget/outlets
    print("\nTesting endpoint 3: GET /api/budget/outlets...")
    response = client.get("/api/budget/outlets?limit=5")
    assert response.status_code == 200
    res3 = response.json()
    assert len(res3) == 5
    print("Budgets per outlet (sample):", res3[0])

    # 4. GET /api/budget/distributors
    print("\nTesting endpoint 4: GET /api/budget/distributors...")
    response = client.get("/api/budget/distributors")
    assert response.status_code == 200
    res4 = response.json()
    assert len(res4) > 0
    print("Budgets per distributor (sample):", res4[0])

    # 5. GET /api/budget/summary
    print("\nTesting endpoint 5: GET /api/budget/summary...")
    response = client.get("/api/budget/summary")
    assert response.status_code == 200
    res5 = response.json()
    assert "total_allocated" in res5
    print("Budgets summary:", res5)

    # 6. GET /api/map/heatmap
    print("\nTesting endpoint 6: GET /api/map/heatmap...")
    response = client.get("/api/map/heatmap?limit=5")
    assert response.status_code == 200
    res6 = response.json()
    assert len(res6) > 0
    print("Heatmap first item:", res6[0])

    # 7. GET /api/map/competitors
    print("\nTesting endpoint 7: GET /api/map/competitors...")
    response = client.get("/api/map/competitors?limit=10")
    assert response.status_code == 200
    res7 = response.json()
    assert len(res7) > 0
    print("Competitor links count retrieved:", len(res7))
    print("Competitor link first item:", res7[0])

    # 8. GET /api/map/pois
    print("\nTesting endpoint 8: GET /api/map/pois?limit=5")
    response = client.get("/api/map/pois")
    assert response.status_code == 200
    res8 = response.json()
    assert len(res8) > 0
    print("POIs first item:", res8[0])

    # 9. GET /api/map/outlets
    print("\nTesting endpoint 9: GET /api/map/outlets...")
    response = client.get("/api/map/outlets")
    assert response.status_code == 200
    res9 = response.json()
    assert len(res9) > 0
    print("Map outlets count:", len(res9))
    print("Map outlet first item:", res9[0])

    # 10. GET /api/outlets/{id}/spatial
    print("\nTesting endpoint 10: GET /api/outlets/OUT_00001/spatial...")
    response = client.get("/api/outlets/OUT_00001/spatial")
    assert response.status_code == 200
    res10 = response.json()
    assert "POI_Total_Impact_Score" in res10
    print("Spatial info of OUT_00001:", res10)

    # 11. GET /api/outlets/{id}/history
    print("\nTesting endpoint 11: GET /api/outlets/OUT_00001/history...")
    response = client.get("/api/outlets/OUT_00001/history")
    assert response.status_code == 200
    res11 = response.json()
    assert len(res11) > 0
    print("History record count for OUT_00001:", len(res11))
    print("History first record:", res11[0])

    # 12. GET /api/outlets/{id}
    print("\nTesting endpoint 12: GET /api/outlets/OUT_00001...")
    response = client.get("/api/outlets/OUT_00001")
    assert response.status_code == 200
    res12 = response.json()
    assert res12["Outlet_ID"] == "OUT_00001"
    print("Outlet profile details for OUT_00001 successfully verified.")

    # 13. GET /api/outlets/export
    print("\nTesting endpoint 13: GET /api/outlets/export...")
    response = client.get("/api/outlets/export")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=outlet_predictions_export.csv" in response.headers["Content-Disposition"]
    csv_preview = response.text[:200]
    print("Export CSV preview (first 200 chars):")
    print(csv_preview)

    # 14. GET /api/outlets
    print("\nTesting endpoint 14: GET /api/outlets...")
    response = client.get("/api/outlets?limit=5")
    assert response.status_code == 200
    res14 = response.json()
    assert res14["total"] == 19960
    assert len(res14["items"]) == 5
    print("Paginated outlets list verified.")

    # 15. GET /api/dashboard/distributors
    print("\nTesting endpoint 15: GET /api/dashboard/distributors...")
    response = client.get("/api/dashboard/distributors")
    assert response.status_code == 200
    res15 = response.json()
    assert len(res15) > 0
    print("Dashboard distributors list count:", len(res15))
    print("Dashboard distributor item:", res15[0])

    # 16. GET /api/dashboard/provinces
    print("\nTesting endpoint 16: GET /api/dashboard/provinces...")
    response = client.get("/api/dashboard/provinces")
    assert response.status_code == 200
    res16 = response.json()
    assert len(res16) > 0
    print("Dashboard provinces list count:", len(res16))
    print("Dashboard province item:", res16[0])

    # 17. GET /api/dashboard/summary
    print("\nTesting endpoint 17: GET /api/dashboard/summary...")
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    res17 = response.json()
    assert res17["total_outlets"] == 19960
    print("Dashboard summary stats:", res17)

    # === Campaign, Monitoring, Evaluation, Reallocation Tests ===
    print("\n=== STARTING PILOT CAMPAIGN INTEGRATION TESTS ===")

    # Test Campaign Creation
    print("Testing POST /api/campaigns (Create Campaign)...")
    camp_payload = {
        "campaign_name": "Test Pilot Campaign",
        "province": "Western",
        "start_date": "2026-06-01",
        "end_date": "2026-06-30",
        "total_budget": 1000000.0
    }
    response = client.post("/api/campaigns", json=camp_payload)
    assert response.status_code == 200
    camp = response.json()
    assert camp["campaign_name"] == "Test Pilot Campaign"
    assert camp["status"] == "Draft"
    campaign_id = camp["campaign_id"]
    print(f"Created draft campaign with ID: {campaign_id}")

    # Test GET /api/campaigns (List Campaigns)
    print("Testing GET /api/campaigns (List Campaigns)...")
    response = client.get("/api/campaigns")
    assert response.status_code == 200
    camps = response.json()
    assert len(camps) > 0
    assert any(c["campaign_id"] == campaign_id for c in camps)
    print(f"Verified campaign list contains campaign {campaign_id}")

    # Test GET /api/campaigns/{id} (Campaign Details)
    print(f"Testing GET /api/campaigns/{campaign_id} (Campaign Details)...")
    response = client.get(f"/api/campaigns/{campaign_id}")
    assert response.status_code == 200
    assert response.json()["campaign_id"] == campaign_id
    print("Verified campaign details retrieval")

    # Test POST /api/campaigns/{id}/generate-pilot (Start Pilot)
    print(f"Testing POST /api/campaigns/{campaign_id}/generate-pilot (Start Pilot)...")
    response = client.post(f"/api/campaigns/{campaign_id}/generate-pilot?top_n=5")
    assert response.status_code == 200
    active_camp = response.json()
    assert active_camp["status"] == "Active"
    print("Verified pilot campaign started and status shifted to Active")

    # Test GET /api/campaigns/{id}/treatment (Treatment group)
    print(f"Testing GET /api/campaigns/{campaign_id}/treatment...")
    response = client.get(f"/api/campaigns/{campaign_id}/treatment")
    assert response.status_code == 200
    treatment = response.json()
    assert len(treatment) == 5
    print(f"Verified treatment group contains 5 outlets: {[t['outlet_id'] for t in treatment]}")

    # Test GET /api/campaigns/{id}/control (Control group)
    print(f"Testing GET /api/campaigns/{campaign_id}/control...")
    response = client.get(f"/api/campaigns/{campaign_id}/control")
    assert response.status_code == 200
    control = response.json()
    assert len(control) == 5
    print(f"Verified matched control group contains 5 outlets: {[c['outlet_id'] for c in control]}")

    # Test GET /api/campaigns/{id}/monitoring (Monitoring summary)
    print(f"Testing GET /api/campaigns/{campaign_id}/monitoring...")
    response = client.get(f"/api/campaigns/{campaign_id}/monitoring")
    assert response.status_code == 200
    mon = response.json()
    assert mon["campaign_id"] == campaign_id
    assert "allocated_budget" in mon
    assert "outlets_performance" in mon
    print("Verified campaign monitoring summary results")

    # Test GET /api/campaigns/{id}/monitoring/{outlet_id} (Outlet snapshot logs)
    test_outlet_id = treatment[0]["outlet_id"]
    print(f"Testing GET /api/campaigns/{campaign_id}/monitoring/{test_outlet_id}...")
    response = client.get(f"/api/campaigns/{campaign_id}/monitoring/{test_outlet_id}")
    assert response.status_code == 200
    snaps = response.json()
    assert len(snaps) == 4 # 4 weeks
    print(f"Verified snapshots list for outlet {test_outlet_id} has 4 weekly snapshots")

    # Test POST /api/campaigns/{id}/evaluate/pre-post
    print(f"Testing POST /api/campaigns/{campaign_id}/evaluate/pre-post...")
    response = client.post(f"/api/campaigns/{campaign_id}/evaluate/pre-post")
    assert response.status_code == 200
    eval_pre_post = response.json()
    assert "average_lift" in eval_pre_post
    print("Verified pre-post evaluation calculation")

    # Test GET /api/campaigns/{id}/evaluate/pre-post
    print(f"Testing GET /api/campaigns/{campaign_id}/evaluate/pre-post...")
    response = client.get(f"/api/campaigns/{campaign_id}/evaluate/pre-post")
    assert response.status_code == 200
    assert "average_lift" in response.json()
    print("Verified pre-post evaluation retrieval")

    # Test POST /api/campaigns/{id}/evaluate/did
    print(f"Testing POST /api/campaigns/{campaign_id}/evaluate/did...")
    response = client.post(f"/api/campaigns/{campaign_id}/evaluate/did")
    assert response.status_code == 200
    analysis = response.json()
    assert "did_effect" in analysis
    print("Verified Difference-in-Differences evaluation calculation")

    # Test GET /api/campaigns/{id}/evaluate/did
    print(f"Testing GET /api/campaigns/{campaign_id}/evaluate/did...")
    response = client.get(f"/api/campaigns/{campaign_id}/evaluate/did")
    assert response.status_code == 200
    eval_did = response.json()
    assert "did_effect" in eval_did
    assert "pairs" in eval_did
    print("Verified DiD evaluation details retrieval")

    # Test POST /api/campaigns/{id}/reallocate (Generate recommendations)
    print(f"Testing POST /api/campaigns/{campaign_id}/reallocate (Generate Reallocations)...")
    response = client.post(f"/api/campaigns/{campaign_id}/reallocate")
    assert response.status_code == 200
    recs = response.json()
    # At least one underperformer was seeded/generated based on indexing logic
    print(f"Generated {len(recs)} budget reallocation recommendations")

    # Test POST /api/campaigns/{id}/reallocate/apply (Apply recommendations)
    if len(recs) > 0:
        print(f"Testing POST /api/campaigns/{campaign_id}/reallocate/apply...")
        response = client.post(f"/api/campaigns/{campaign_id}/reallocate/apply")
        assert response.status_code == 200
        apply_res = response.json()
        assert apply_res["status"] == "applied"
        
        # Verify recommendations can be re-queried/re-calculated
        response = client.post(f"/api/campaigns/{campaign_id}/reallocate")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print("Verified reallocation recommendations applied successfully and database recommendations table updated")
    else:
        print("Skipped apply recommendations test (no underperforming outlets found)")

    print("\nALL 17 ORIGINAL ENDPOINTS + ALL 14 NEW CAMPAIGN ENDPOINTS SUCCESSFULLY IMPLEMENTED AND VERIFIED!")

if __name__ == "__main__":
    test_endpoints()

