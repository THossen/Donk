"""Investigation threads: list, reopen, delete completed investigations."""
from fastapi import APIRouter, HTTPException

from .. import context as ctx

router = APIRouter()


@router.get("/api/investigations")
def list_investigations(limit: int = 20):
    limit = max(1, min(limit, 100))
    return {"investigations": ctx.store.list_investigations(limit)}


@router.get("/api/investigations/{inv_id}")
def get_investigation(inv_id: str):
    inv = ctx.store.get_investigation(inv_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="unknown investigation")
    return inv


@router.delete("/api/investigations/{inv_id}")
def delete_investigation(inv_id: str):
    if not ctx.store.delete_investigation(inv_id):
        raise HTTPException(status_code=404, detail="unknown investigation")
    return {"deleted": inv_id}


@router.delete("/api/investigations")
def clear_investigations():
    return {"deleted": ctx.store.clear_investigations()}
