from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..errors import AppError
from ..models import Course, Lecture
from ..services.exporters import course_body, lecture_markdown, markdown_to_docx, markdown_to_pdf, obsidian_zip
from ..utils.security import sanitize_filename

router = APIRouter(tags=["exports"])


def download(data: bytes | str, filename: str, media_type: str) -> Response:
    return Response(content=data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/api/lectures/{lecture_id}/export/markdown")
def lecture_md(lecture_id: int, db: Session = Depends(get_db)):
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise AppError("RESOURCE_NOT_FOUND", "Lecture not found.", 404)
    return download(lecture_markdown(lecture), f"{sanitize_filename(lecture.title)}.md", "text/markdown")


@router.get("/api/lectures/{lecture_id}/export/docx")
def lecture_docx(lecture_id: int, db: Session = Depends(get_db)):
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise AppError("RESOURCE_NOT_FOUND", "Lecture not found.", 404)
    return download(markdown_to_docx(lecture.title, lecture_markdown(lecture)), f"{sanitize_filename(lecture.title)}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/api/lectures/{lecture_id}/export/pdf")
def lecture_pdf(lecture_id: int, db: Session = Depends(get_db)):
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise AppError("RESOURCE_NOT_FOUND", "Lecture not found.", 404)
    return download(markdown_to_pdf(lecture.title, lecture_markdown(lecture)), f"{sanitize_filename(lecture.title)}.pdf", "application/pdf")


@router.get("/api/courses/{course_id}/export/obsidian")
def course_obsidian(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise AppError("RESOURCE_NOT_FOUND", "Course not found.", 404)
    return download(obsidian_zip(course), f"{sanitize_filename(course.title)}-obsidian.zip", "application/zip")


@router.get("/api/courses/{course_id}/export/markdown")
def course_md(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise AppError("RESOURCE_NOT_FOUND", "Course not found.", 404)
    return download(course_body(course), f"{sanitize_filename(course.title)}.md", "text/markdown")


@router.get("/api/courses/{course_id}/export/docx")
def course_docx(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise AppError("RESOURCE_NOT_FOUND", "Course not found.", 404)
    return download(markdown_to_docx(course.title, course_body(course)), f"{sanitize_filename(course.title)}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/api/courses/{course_id}/export/pdf")
def course_pdf(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise AppError("RESOURCE_NOT_FOUND", "Course not found.", 404)
    return download(markdown_to_pdf(course.title, course_body(course)), f"{sanitize_filename(course.title)}.pdf", "application/pdf")
