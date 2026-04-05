from types import SimpleNamespace

import app as _app


class TraceabilityService:
    @staticmethod
    def create_link(acceptance_test_id, requirement_id=None, user_story_id=None):
        res = _app.supabase.table("requirement_test_links").insert({
            "acceptance_test_id": acceptance_test_id,
            "requirement_id": requirement_id or None,
            "user_story_id": user_story_id or None,
        }).execute()
        return SimpleNamespace(**res.data[0])

    @staticmethod
    def get_links_for_acceptance_test(acceptance_test_id):
        res = (
            _app.supabase.table("requirement_test_links")
            .select("*")
            .eq("acceptance_test_id", acceptance_test_id)
            .execute()
        )
        return [SimpleNamespace(**d) for d in res.data]

    @staticmethod
    def get_links_for_requirement(requirement_id):
        res = (
            _app.supabase.table("requirement_test_links")
            .select("*")
            .eq("requirement_id", requirement_id)
            .execute()
        )
        return [SimpleNamespace(**d) for d in res.data]

    @staticmethod
    def get_links_for_user_story(user_story_id):
        res = (
            _app.supabase.table("requirement_test_links")
            .select("*")
            .eq("user_story_id", user_story_id)
            .execute()
        )
        return [SimpleNamespace(**d) for d in res.data]

    @staticmethod
    def get_link(link_id):
        res = (
            _app.supabase.table("requirement_test_links")
            .select("*")
            .eq("id", link_id)
            .maybe_single()
            .execute()
        )
        return SimpleNamespace(**res.data) if res.data else None

    @staticmethod
    def delete_link(link):
        _app.supabase.table("requirement_test_links").delete().eq("id", link.id).execute()

    @staticmethod
    def get_traceability_map(project_id):
        from app.services.document_service import DocumentService
        acceptance_tests = DocumentService.get_all_for_project(project_id, doc_type="acceptance_test")
        result = []
        for at in acceptance_tests:
            links = TraceabilityService.get_links_for_acceptance_test(at.id)
            req_ids = [l.requirement_id for l in links if l.requirement_id]
            us_ids = [l.user_story_id for l in links if l.user_story_id]
            if req_ids or us_ids:
                result.append({
                    "acceptance_test_id": at.id,
                    "requirement_ids": req_ids,
                    "user_story_ids": us_ids,
                })
        return result
