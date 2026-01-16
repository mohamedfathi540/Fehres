from minirag_base import SQLAlchemyBase
from sqlalchemy import Column , Integer , String , Boolean , DateTime , func , JSON , ForeignKey
from sqlalchemy.dialects.postgresql import UUID , JSONB
import uuid 
from sqlalchemy.orm import relationship
from sqlalchemy import Index


class Asset(SQLAlchemyBase) :
    __tablename__ = "assets"

    asset_id = Column(Integer , primary_key = True , autoincrement = True)
    asset_uuid = Column(UUID(as_uuid = True) , default = uuid.uuid4 , unique = True, nullable = False)
    
    
    asset_type = Column(String , nullable = False)
    asset_name = Column(String , nullable = False)
    asset_size = Column(Integer , nullable = True)
    asset_pushed_at = Column(DateTime(timezone = True) , server_default = func.now(), nullable = False)
    asset_config = Column(JSONB , nullable = True)


    asset_project_id = Column(Integer , ForeignKey("projects.project_id"), nullable = False)
    project = relationship("Project" , back_populates = "assets")

    __table_args__ = (Index("ix_asset_project_id" , asset_project_id),
                    Index("ix_asset_type",asset_type))


    create_at  =Column(DateTime(timezone = True) , server_default = func.now(), nullable = False)
    update_at  =Column(DateTime(timezone = True) , onupdate = func.now(), nullable = False)