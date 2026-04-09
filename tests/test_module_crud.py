"""Tests for the Module CRUD feature and document-module association."""

import pytest


@pytest.fixture
def module_data():
    return {"name": "Authentication", "description": "Auth module"}


class TestModuleService:
    def test_create_module(self, app, project):
        from app.services.module_service import ModuleService
        mod = ModuleService.create(project.id, "Auth", description="Auth module")
        assert mod.name == "Auth"
        assert mod.description == "Auth module"
        assert mod.project_id == project.id
        assert mod.parent_id is None

    def test_get_module(self, app, project):
        from app.services.module_service import ModuleService
        created = ModuleService.create(project.id, "Payments")
        fetched = ModuleService.get(created.id)
        assert fetched is not None
        assert fetched.name == "Payments"

    def test_get_all_for_project(self, app, project):
        from app.services.module_service import ModuleService
        ModuleService.create(project.id, "Auth")
        ModuleService.create(project.id, "Payments")
        modules = ModuleService.get_all_for_project(project.id)
        assert len(modules) == 2

    def test_update_module(self, app, project):
        from app.services.module_service import ModuleService
        mod = ModuleService.create(project.id, "Auth")
        ModuleService.update(mod, name="Authentication")
        fetched = ModuleService.get(mod.id)
        assert fetched.name == "Authentication"

    def test_delete_module(self, app, project):
        from app.services.module_service import ModuleService
        mod = ModuleService.create(project.id, "Auth")
        ModuleService.delete(mod)
        assert ModuleService.get(mod.id) is None

    def test_tree_building(self, app, project):
        from app.services.module_service import ModuleService
        parent = ModuleService.create(project.id, "Auth")
        child1 = ModuleService.create(project.id, "OAuth", parent_id=parent.id)
        child2 = ModuleService.create(project.id, "Sessions", parent_id=parent.id)
        ModuleService.create(project.id, "Payments")

        tree = ModuleService.get_tree_for_project(project.id)
        assert len(tree) == 2  # Auth and Payments at root

        auth_node = next(n for n in tree if n.name == "Auth")
        assert len(auth_node.children) == 2
        child_names = {c.name for c in auth_node.children}
        assert child_names == {"OAuth", "Sessions"}

    def test_delete_module_reparents_children(self, app, project):
        from app.services.module_service import ModuleService
        grandparent = ModuleService.create(project.id, "Backend")
        parent = ModuleService.create(project.id, "Auth", parent_id=grandparent.id)
        child = ModuleService.create(project.id, "OAuth", parent_id=parent.id)

        ModuleService.delete(parent)

        # Child should now be under grandparent
        updated_child = ModuleService.get(child.id)
        assert updated_child.parent_id == grandparent.id


class TestDocumentModuleAssociation:
    def test_create_document_with_module(self, app, project):
        from app.services.module_service import ModuleService
        from app.services.document_service import DocumentService

        mod = ModuleService.create(project.id, "Auth")
        doc = DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "JWT Auth"},
            module_id=mod.id,
        )
        assert doc.module_id == mod.id

    def test_update_document_module(self, app, project):
        from app.services.module_service import ModuleService
        from app.services.document_service import DocumentService

        mod1 = ModuleService.create(project.id, "Auth")
        mod2 = ModuleService.create(project.id, "Payments")
        doc = DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "JWT Auth"},
            module_id=mod1.id,
        )
        DocumentService.update(doc, module_id=mod2.id)
        fetched = DocumentService.get(doc.id)
        assert fetched.module_id == mod2.id

    def test_unassign_document_from_module(self, app, project):
        from app.services.module_service import ModuleService
        from app.services.document_service import DocumentService

        mod = ModuleService.create(project.id, "Auth")
        doc = DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "JWT Auth"},
            module_id=mod.id,
        )
        DocumentService.update(doc, module_id="")
        fetched = DocumentService.get(doc.id)
        assert fetched.module_id is None

    def test_delete_module_unassigns_documents(self, app, project):
        from app.services.module_service import ModuleService
        from app.services.document_service import DocumentService

        mod = ModuleService.create(project.id, "Auth")
        doc = DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "JWT Auth"},
            module_id=mod.id,
        )
        ModuleService.delete(mod)

        fetched = DocumentService.get(doc.id)
        assert fetched.module_id is None

    def test_filter_documents_by_module(self, app, project):
        from app.services.module_service import ModuleService
        from app.services.document_service import DocumentService

        mod = ModuleService.create(project.id, "Auth")
        DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "JWT Auth"},
            module_id=mod.id,
        )
        DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "Stripe Integration"},
        )
        auth_docs = DocumentService.get_all_for_project(project.id, module_id=mod.id)
        all_docs = DocumentService.get_all_for_project(project.id)
        assert len(auth_docs) == 1
        assert len(all_docs) == 2


class TestModuleRoutes:
    def test_create_module_page(self, client, project):
        resp = client.get(f"/projects/{project.id}/modules/new")
        assert resp.status_code == 200

    def test_create_module_post(self, client, project):
        resp = client.post(
            f"/projects/{project.id}/modules/new",
            data={"name": "Auth", "description": "Authentication module", "parent_id": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        from app.services.module_service import ModuleService
        modules = ModuleService.get_all_for_project(project.id)
        assert len(modules) == 1
        assert modules[0].name == "Auth"

    def test_edit_module(self, client, project):
        from app.services.module_service import ModuleService
        mod = ModuleService.create(project.id, "Auth")

        resp = client.get(f"/projects/{project.id}/modules/{mod.id}/edit")
        assert resp.status_code == 200

        resp = client.post(
            f"/projects/{project.id}/modules/{mod.id}/edit",
            data={"name": "Authentication", "description": "Updated", "parent_id": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        updated = ModuleService.get(mod.id)
        assert updated.name == "Authentication"

    def test_delete_module(self, client, project):
        from app.services.module_service import ModuleService
        mod = ModuleService.create(project.id, "Auth")

        resp = client.post(
            f"/projects/{project.id}/modules/{mod.id}/delete",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert ModuleService.get(mod.id) is None

    def test_documents_index_with_modules(self, client, project):
        from app.services.module_service import ModuleService
        from app.services.document_service import DocumentService

        mod = ModuleService.create(project.id, "Auth")
        DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "JWT Auth"},
            module_id=mod.id,
        )
        DocumentService.create(
            project_id=project.id,
            doc_type="requirement",
            data={"title": "Unassigned Req"},
        )

        resp = client.get(f"/projects/{project.id}/documents")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Auth" in html
        assert "JWT Auth" in html
        assert "Unassigned Req" in html
