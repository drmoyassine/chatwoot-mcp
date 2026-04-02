"""
Test suite for MCP Hub Marketplace API endpoints
Tests: /api/marketplace/catalog, /api/marketplace/publish, DELETE /api/marketplace/{slug}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMarketplaceCatalog:
    """Tests for GET /api/marketplace/catalog - public endpoint"""
    
    def test_catalog_returns_curated_servers(self):
        """GET /api/marketplace/catalog returns curated servers (12 entries)"""
        response = requests.get(f"{BASE_URL}/api/marketplace/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "catalog" in data
        assert "categories" in data
        
        # Should have at least 12 curated servers
        catalog = data["catalog"]
        assert len(catalog) >= 12, f"Expected at least 12 curated servers, got {len(catalog)}"
        
        # Check structure of first entry
        first = catalog[0]
        assert "slug" in first
        assert "name" in first
        assert "description" in first
        assert "category" in first
        assert "runtime" in first
        assert "source" in first
        print(f"✓ Catalog returned {len(catalog)} servers with {len(data['categories'])} categories")
    
    def test_catalog_filter_by_category(self):
        """GET /api/marketplace/catalog?category=developer filters by category"""
        response = requests.get(f"{BASE_URL}/api/marketplace/catalog?category=developer")
        assert response.status_code == 200
        
        data = response.json()
        catalog = data["catalog"]
        
        # All entries should be developer category
        for entry in catalog:
            assert entry["category"] == "developer", f"Expected developer category, got {entry['category']}"
        
        # Should have at least GitHub and GitLab
        slugs = [e["slug"] for e in catalog]
        assert "github" in slugs, "GitHub should be in developer category"
        assert "gitlab" in slugs, "GitLab should be in developer category"
        print(f"✓ Category filter returned {len(catalog)} developer servers")
    
    def test_catalog_filter_by_search(self):
        """GET /api/marketplace/catalog?search=github filters by search term"""
        response = requests.get(f"{BASE_URL}/api/marketplace/catalog?search=github")
        assert response.status_code == 200
        
        data = response.json()
        catalog = data["catalog"]
        
        # Should find GitHub server
        assert len(catalog) >= 1, "Should find at least one result for 'github'"
        
        # Check that search matches name or description
        for entry in catalog:
            name_match = "github" in entry["name"].lower()
            desc_match = "github" in entry["description"].lower()
            slug_match = "github" in entry["slug"].lower()
            assert name_match or desc_match or slug_match, f"Entry {entry['slug']} doesn't match 'github'"
        print(f"✓ Search filter returned {len(catalog)} results for 'github'")
    
    def test_catalog_combined_filters(self):
        """GET /api/marketplace/catalog with both category and search"""
        response = requests.get(f"{BASE_URL}/api/marketplace/catalog?category=database&search=postgres")
        assert response.status_code == 200
        
        data = response.json()
        catalog = data["catalog"]
        
        # Should find PostgreSQL
        assert len(catalog) >= 1, "Should find PostgreSQL"
        assert any(e["slug"] == "postgres" for e in catalog), "PostgreSQL should be in results"
        print(f"✓ Combined filters returned {len(catalog)} results")
    
    def test_catalog_returns_categories_list(self):
        """GET /api/marketplace/catalog returns list of available categories"""
        response = requests.get(f"{BASE_URL}/api/marketplace/catalog")
        assert response.status_code == 200
        
        data = response.json()
        categories = data["categories"]
        
        # Should have multiple categories
        assert len(categories) >= 5, f"Expected at least 5 categories, got {len(categories)}"
        
        # Check expected categories exist
        expected = ["developer", "database", "utility", "communication"]
        for cat in expected:
            assert cat in categories, f"Expected category '{cat}' not found"
        print(f"✓ Catalog returned categories: {categories}")


class TestMarketplacePublish:
    """Tests for POST /api/marketplace/publish - requires admin auth"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for protected endpoints"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@mcphub.local",
            "password": "McpHub2026!"
        })
        if login_resp.status_code == 200:
            token = login_resp.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
        self.session.close()
    
    def test_publish_requires_auth(self):
        """POST /api/marketplace/publish requires authentication"""
        response = requests.post(f"{BASE_URL}/api/marketplace/publish", json={
            "server_name": "test-server"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Publish endpoint requires authentication")
    
    def test_publish_returns_404_for_nonexistent_server(self):
        """POST /api/marketplace/publish returns 404 for non-existent server"""
        response = self.session.post(f"{BASE_URL}/api/marketplace/publish", json={
            "server_name": "nonexistent-server-xyz"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
        print("✓ Publish returns 404 for non-existent server")
    
    def test_publish_requires_server_name(self):
        """POST /api/marketplace/publish requires server_name"""
        response = self.session.post(f"{BASE_URL}/api/marketplace/publish", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Publish requires server_name parameter")
    
    def test_publish_and_unpublish_flow(self):
        """Full flow: install server -> publish -> verify in catalog -> unpublish"""
        # First, add a test server
        test_server_name = "test-marketplace-publish"
        
        # Clean up if exists
        self.session.delete(f"{BASE_URL}/api/servers/{test_server_name}")
        self.session.delete(f"{BASE_URL}/api/marketplace/{test_server_name}")
        
        # Add server
        add_resp = self.session.post(f"{BASE_URL}/api/servers/add", json={
            "name": test_server_name,
            "display_name": "Test Marketplace Server",
            "description": "A test server for marketplace testing",
            "runtime": "node",
            "command": "npx",
            "args": ["-y", "@test/server"],
            "credentials_schema": []
        })
        assert add_resp.status_code in [200, 201, 409], f"Failed to add server: {add_resp.text}"
        
        # Publish to marketplace
        publish_resp = self.session.post(f"{BASE_URL}/api/marketplace/publish", json={
            "server_name": test_server_name,
            "description": "Published test server",
            "category": "community"
        })
        assert publish_resp.status_code == 200, f"Failed to publish: {publish_resp.text}"
        
        data = publish_resp.json()
        assert data.get("status") == "published"
        assert data.get("slug") == test_server_name
        print(f"✓ Published server to marketplace: {test_server_name}")
        
        # Verify in catalog
        catalog_resp = requests.get(f"{BASE_URL}/api/marketplace/catalog")
        catalog = catalog_resp.json()["catalog"]
        published = next((e for e in catalog if e["slug"] == test_server_name), None)
        assert published is not None, "Published server not found in catalog"
        assert published["source"] == "community"
        print("✓ Published server appears in catalog with source='community'")
        
        # Try to publish again - should get 409
        dup_resp = self.session.post(f"{BASE_URL}/api/marketplace/publish", json={
            "server_name": test_server_name
        })
        assert dup_resp.status_code == 409, f"Expected 409 for duplicate, got {dup_resp.status_code}"
        print("✓ Duplicate publish returns 409")
        
        # Unpublish
        unpub_resp = self.session.delete(f"{BASE_URL}/api/marketplace/{test_server_name}")
        assert unpub_resp.status_code == 200, f"Failed to unpublish: {unpub_resp.text}"
        print("✓ Unpublished server from marketplace")
        
        # Verify removed from catalog
        catalog_resp2 = requests.get(f"{BASE_URL}/api/marketplace/catalog")
        catalog2 = catalog_resp2.json()["catalog"]
        still_there = any(e["slug"] == test_server_name for e in catalog2)
        assert not still_there, "Server should be removed from catalog after unpublish"
        print("✓ Server removed from catalog after unpublish")
        
        # Cleanup - remove test server
        self.session.delete(f"{BASE_URL}/api/servers/{test_server_name}")


class TestMarketplaceUnpublish:
    """Tests for DELETE /api/marketplace/{slug}"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@mcphub.local",
            "password": "McpHub2026!"
        })
        if login_resp.status_code == 200:
            token = login_resp.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
        self.session.close()
    
    def test_unpublish_requires_auth(self):
        """DELETE /api/marketplace/{slug} requires authentication"""
        response = requests.delete(f"{BASE_URL}/api/marketplace/some-server")
        assert response.status_code == 401
        print("✓ Unpublish endpoint requires authentication")
    
    def test_unpublish_returns_404_for_nonexistent(self):
        """DELETE /api/marketplace/{slug} returns 404 for non-existent entry"""
        response = self.session.delete(f"{BASE_URL}/api/marketplace/nonexistent-xyz-123")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Unpublish returns 404 for non-existent entry")


class TestMarketplaceInstalledFlag:
    """Tests for installed flag on catalog entries"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@mcphub.local",
            "password": "McpHub2026!"
        })
        if login_resp.status_code == 200:
            token = login_resp.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
        self.session.close()
    
    def test_installed_flag_on_catalog_entries(self):
        """Catalog entries have installed=true when server is installed"""
        test_server_slug = "github"  # Use a curated server
        
        # First check if github is already installed
        catalog_resp = requests.get(f"{BASE_URL}/api/marketplace/catalog")
        catalog = catalog_resp.json()["catalog"]
        github_entry = next((e for e in catalog if e["slug"] == test_server_slug), None)
        
        assert github_entry is not None, "GitHub should be in catalog"
        assert "installed" in github_entry, "Entry should have 'installed' field"
        
        initial_installed = github_entry["installed"]
        print(f"✓ GitHub entry has installed={initial_installed}")
        
        # If not installed, install it and verify flag changes
        if not initial_installed:
            # Install github server
            add_resp = self.session.post(f"{BASE_URL}/api/servers/add", json={
                "name": test_server_slug,
                "display_name": github_entry["name"],
                "description": github_entry["description"],
                "runtime": github_entry["runtime"],
                "command": github_entry["command"],
                "args": github_entry["args"],
                "npm_package": github_entry.get("npm_package", ""),
                "credentials_schema": github_entry.get("credentials_schema", [])
            })
            
            if add_resp.status_code in [200, 201]:
                # Check catalog again
                catalog_resp2 = requests.get(f"{BASE_URL}/api/marketplace/catalog")
                catalog2 = catalog_resp2.json()["catalog"]
                github_entry2 = next((e for e in catalog2 if e["slug"] == test_server_slug), None)
                
                assert github_entry2["installed"] == True, "After install, installed should be True"
                print("✓ After installing, installed flag is True")
                
                # Cleanup
                self.session.delete(f"{BASE_URL}/api/servers/{test_server_slug}")
        else:
            print("✓ GitHub already installed, installed=True verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
