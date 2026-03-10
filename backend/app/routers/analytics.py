"""Router for analytics endpoints.

Each endpoint performs SQL aggregation queries on the interaction data
populated by the ETL pipeline. All endpoints require a `lab` query
parameter to filter results by lab (e.g., "lab-01").
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlmodel import select as sqlmodel_select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.item import ItemRecord
from app.models.learner import Learner
from app.models.interaction import InteractionLog

router = APIRouter()


@router.get("/scores")
async def get_scores(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Score distribution histogram for a given lab.

    - Find the lab item by matching title (e.g. "lab-04" → title contains "Lab 04")
    - Find all tasks that belong to this lab (parent_id = lab.id)
    - Query interactions for these items that have a score
    - Group scores into buckets: "0-25", "26-50", "51-75", "76-100"
      using CASE WHEN expressions
    - Return a JSON array:
      [{"bucket": "0-25", "count": 12}, {"bucket": "26-50", "count": 8}, ...]
    - Always return all four buckets, even if count is 0
    """
    # Parse lab identifier: "lab-04" → "Lab 04"
    lab_title = lab.replace("-", " ").replace("lab ", "Lab ", 1).title()
    if "Lab " not in lab_title:
        lab_title = "Lab " + lab_title

    # Find the lab item
    lab_stmt = sqlmodel_select(ItemRecord).where(
        ItemRecord.type == "lab",
        ItemRecord.title.ilike(f"%{lab_title}%")
    )
    lab_item = (await session.exec(lab_stmt)).first()

    if not lab_item:
        return [
            {"bucket": "0-25", "count": 0},
            {"bucket": "26-50", "count": 0},
            {"bucket": "51-75", "count": 0},
            {"bucket": "76-100", "count": 0},
        ]

    # Find all task items for this lab
    task_stmt = sqlmodel_select(ItemRecord.id).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_item.id
    )
    task_ids = list((await session.exec(task_stmt)).all())

    if not task_ids:
        return [
            {"bucket": "0-25", "count": 0},
            {"bucket": "26-50", "count": 0},
            {"bucket": "51-75", "count": 0},
            {"bucket": "76-100", "count": 0},
        ]

    # Build CASE WHEN expression for buckets
    bucket_case = case(
        (InteractionLog.score <= 25, "0-25"),
        (InteractionLog.score <= 50, "26-50"),
        (InteractionLog.score <= 75, "51-75"),
        else_="76-100"
    )

    # Query score distribution
    stmt = select(
        bucket_case.label("bucket"),
        func.count(InteractionLog.id).label("count")
    ).where(
        InteractionLog.item_id.in_(task_ids),
        InteractionLog.score.isnot(None)
    ).group_by(bucket_case)

    result = await session.exec(stmt)
    rows = result.all()

    # Build result with all buckets
    bucket_counts = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    for bucket, count in rows:
        bucket_counts[bucket] = count

    return [
        {"bucket": "0-25", "count": bucket_counts["0-25"]},
        {"bucket": "26-50", "count": bucket_counts["26-50"]},
        {"bucket": "51-75", "count": bucket_counts["51-75"]},
        {"bucket": "76-100", "count": bucket_counts["76-100"]},
    ]


@router.get("/pass-rates")
async def get_pass_rates(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Per-task pass rates for a given lab.

    - Find the lab item and its child task items
    - For each task, compute:
      - avg_score: average of interaction scores (round to 1 decimal)
      - attempts: total number of interactions
    - Return a JSON array:
      [{"task": "Repository Setup", "avg_score": 92.3, "attempts": 150}, ...]
    - Order by task title
    """
    # Parse lab identifier: "lab-04" → "Lab 04"
    lab_title = lab.replace("-", " ").replace("lab ", "Lab ", 1).title()
    if "Lab " not in lab_title:
        lab_title = "Lab " + lab_title

    # Find the lab item
    lab_stmt = sqlmodel_select(ItemRecord).where(
        ItemRecord.type == "lab",
        ItemRecord.title.ilike(f"%{lab_title}%")
    )
    lab_item = (await session.exec(lab_stmt)).first()

    if not lab_item:
        return []

    # Find all task items for this lab
    task_stmt = sqlmodel_select(ItemRecord).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_item.id
    ).order_by(ItemRecord.title)
    tasks = list((await session.exec(task_stmt)).all())

    result = []
    for task in tasks:
        # Get avg_score and attempts for this task
        stats_stmt = select(
            func.avg(InteractionLog.score).label("avg_score"),
            func.count(InteractionLog.id).label("attempts")
        ).where(
            InteractionLog.item_id == task.id,
            InteractionLog.score.isnot(None)
        )
        stats_result = await session.exec(stats_stmt)
        row = stats_result.first()

        avg_score = round(row[0], 1) if row[0] is not None else 0.0
        attempts = row[1] if row[1] is not None else 0

        result.append({
            "task": task.title,
            "avg_score": avg_score,
            "attempts": attempts,
        })

    return result


@router.get("/timeline")
async def get_timeline(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Submissions per day for a given lab.

    - Find the lab item and its child task items
    - Group interactions by date (use func.date(created_at))
    - Count the number of submissions per day
    - Return a JSON array:
      [{"date": "2026-02-28", "submissions": 45}, ...]
    - Order by date ascending
    """
    # Parse lab identifier: "lab-04" → "Lab 04"
    lab_title = lab.replace("-", " ").replace("lab ", "Lab ", 1).title()
    if "Lab " not in lab_title:
        lab_title = "Lab " + lab_title

    # Find the lab item
    lab_stmt = sqlmodel_select(ItemRecord).where(
        ItemRecord.type == "lab",
        ItemRecord.title.ilike(f"%{lab_title}%")
    )
    lab_item = (await session.exec(lab_stmt)).first()

    if not lab_item:
        return []

    # Find all task items for this lab
    task_stmt = sqlmodel_select(ItemRecord.id).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_item.id
    )
    task_ids = list((await session.exec(task_stmt)).all())

    if not task_ids:
        return []

    # Query submissions per day
    stmt = select(
        func.date(InteractionLog.created_at).label("date"),
        func.count(InteractionLog.id).label("submissions")
    ).where(
        InteractionLog.item_id.in_(task_ids)
    ).group_by(
        func.date(InteractionLog.created_at)
    ).order_by(
        func.date(InteractionLog.created_at)
    )

    result = await session.exec(stmt)
    rows = result.all()

    return [
        {"date": str(date), "submissions": count}
        for date, count in rows
    ]


@router.get("/groups")
async def get_groups(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Per-group performance for a given lab.

    - Find the lab item and its child task items
    - Join interactions with learners to get student_group
    - For each group, compute:
      - avg_score: average score (round to 1 decimal)
      - students: count of distinct learners
    - Return a JSON array:
      [{"group": "B23-CS-01", "avg_score": 78.5, "students": 25}, ...]
    - Order by group name
    """
    # Parse lab identifier: "lab-04" → "Lab 04"
    lab_title = lab.replace("-", " ").replace("lab ", "Lab ", 1).title()
    if "Lab " not in lab_title:
        lab_title = "Lab " + lab_title

    # Find the lab item
    lab_stmt = sqlmodel_select(ItemRecord).where(
        ItemRecord.type == "lab",
        ItemRecord.title.ilike(f"%{lab_title}%")
    )
    lab_item = (await session.exec(lab_stmt)).first()

    if not lab_item:
        return []

    # Find all task items for this lab
    task_stmt = sqlmodel_select(ItemRecord.id).where(
        ItemRecord.type == "task",
        ItemRecord.parent_id == lab_item.id
    )
    task_ids = list((await session.exec(task_stmt)).all())

    if not task_ids:
        return []

    # Query per-group stats
    stmt = select(
        Learner.student_group.label("group"),
        func.avg(InteractionLog.score).label("avg_score"),
        func.count(func.distinct(InteractionLog.learner_id)).label("students")
    ).join(
        Learner, InteractionLog.learner_id == Learner.id
    ).where(
        InteractionLog.item_id.in_(task_ids),
        InteractionLog.score.isnot(None)
    ).group_by(
        Learner.student_group
    ).order_by(
        Learner.student_group
    )

    result = await session.exec(stmt)
    rows = result.all()

    return [
        {
            "group": group,
            "avg_score": round(avg_score, 1) if avg_score is not None else 0.0,
            "students": students,
        }
        for group, avg_score, students in rows
    ]
