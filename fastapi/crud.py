"""Todas as consultas ao banco via SQLModel (sem SQL raw)."""

from sqlmodel import Session, select

from models.tables import Prediction, User


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def get_prediction_for_owner(
    session: Session, prediction_id: int, owner_id: int
) -> Prediction | None:
    """Ownership na própria consulta (anti-BOLA): recurso de outro usuário volta como None."""
    stmt = select(Prediction).where(Prediction.id == prediction_id, Prediction.owner_id == owner_id)
    return session.exec(stmt).first()


def list_predictions_by_owner(session: Session, owner_id: int) -> list[Prediction]:
    stmt = select(Prediction).where(Prediction.owner_id == owner_id).order_by(Prediction.id)
    return list(session.exec(stmt).all())


def create_prediction(
    session: Session, owner_id: int, text: str, intent: str, confidence: float
) -> Prediction:
    prediction = Prediction(owner_id=owner_id, text=text, intent=intent, confidence=confidence)
    session.add(prediction)
    session.commit()
    session.refresh(prediction)
    return prediction
