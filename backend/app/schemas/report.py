from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ReportUploadResponse(BaseModel):
    report_id: str = Field(..., description="报告唯一标识")
    filename: str = Field(..., description="原始文件名")
    status: str = Field(default="uploaded", description="上传状态")
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReportInterpretRequest(BaseModel):
    pass  # 无额外参数，所需数据从上传的文件中提取


class ReportSection(BaseModel):
    title: str = Field(..., description="报告段落标题")
    content: str = Field(..., description="段落原文或结构化内容")


class ReportInterpretResponse(BaseModel):
    report_id: str = Field(..., description="报告唯一标识")
    summary: str = Field(..., description="报告概要")
    sections: list[ReportSection] = Field(default_factory=list, description="结构化段落")
    disclaimer: str = Field(
        default="本解读由 AI 生成，不构成医疗诊断建议。如有疑问，请咨询专业医生。",
        description="免责声明",
    )
