from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.base import SourceFieldImport
import csv
import io
from pydantic import BaseModel
from typing import Optional
router = APIRouter()


def _normalize_lookup_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()

class SourceFieldCreate(BaseModel):
    seq_no: Optional[str] = None
    table_cn: Optional[str] = None
    table_en: Optional[str] = None
    sys_code: Optional[str] = None
    table_def: Optional[str] = None
    field_cn: Optional[str] = None
    field_en: Optional[str] = None
    field_desc: Optional[str] = None
    data_type: Optional[str] = None
    length_precision: Optional[str] = None
    scale: Optional[str] = None
    pk_fk: Optional[str] = None
    is_ref_data: Optional[str] = None
    ref_data_desc: Optional[str] = None
    ref_table_en: Optional[str] = None
    ref_data_usage_desc: Optional[str] = None
    is_history: Optional[str] = None
    mod_status: Optional[str] = None
    mod_time: Optional[str] = None
    mod_reason: Optional[str] = None
    app_scope: Optional[str] = None

class SourceFieldUpdate(SourceFieldCreate):
    pass


@router.post("/source_fields/import")
async def upload_source_fields(
    file: UploadFile = File(...),
    clear_existing: bool = Form(True),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        contents = await file.read()
        try:
            # 尝试优先以 utf-8 解码（处理 BOM）
            decoded_content = contents.decode('utf-8-sig')
        except UnicodeDecodeError:
            # 如果是 GBK / ANSI 格式的 Excel 导出文件，退级使用 gbk 解码
            decoded_content = contents.decode('gbk', errors='replace')
            
        reader = csv.reader(io.StringIO(decoded_content))
        
        # 提取表头并简单校验
        header = next(reader, None)
        if not header or len(header) < 5:
            raise ValueError("CSV 文件的表头格式不正确，列数过少，请参考模板格式！")
        
        imported_records = []
        error_rows = []
        
        for i, row in enumerate(reader):
            # 过滤掉完全为空的行，或者是只有空字符串的行
            if not row or len(row) == 0 or not any(str(col).strip() for col in row):
                continue
                
            try:
                # 自动处理单元格内的换行、回车等特殊不可见字符，替换为空格，避免解析出乱码
                cleaned_row = []
                for col in row:
                    if isinstance(col, str):
                        col = col.replace('\n', ' ').replace('\r', ' ').strip()
                    cleaned_row.append(col)
                
                # 补齐长度以防列数不够（基于最新的 21 个字段模板）
                while len(cleaned_row) < 21:
                    cleaned_row.append(None)
                    
                imported_records.append(SourceFieldImport(
                    seq_no=cleaned_row[0],
                    table_cn=cleaned_row[1],
                    table_en=cleaned_row[2],
                    sys_code=cleaned_row[3],
                    table_def=cleaned_row[4],
                    field_cn=cleaned_row[5],
                    field_en=cleaned_row[6],
                    field_desc=cleaned_row[7],
                    data_type=cleaned_row[8],
                    length_precision=cleaned_row[9],
                    scale=cleaned_row[10],
                    pk_fk=cleaned_row[11],
                    is_ref_data=cleaned_row[12],
                    ref_data_desc=cleaned_row[13],
                    ref_table_en=cleaned_row[14],
                    ref_data_usage_desc=cleaned_row[15],
                    is_history=cleaned_row[16],
                    mod_status=cleaned_row[17],
                    mod_time=cleaned_row[18],
                    mod_reason=cleaned_row[19],
                    app_scope=cleaned_row[20]
                ))
            except Exception as row_e:
                error_rows.append(f"第 {i+2} 行解析异常: {str(row_e)}")
                
        if error_rows:
            db.rollback()
            raise ValueError(f"解析过程中发现 {len(error_rows)} 条数据错误，已全部回滚。前3条错误: " + " | ".join(error_rows[:3]))

        if clear_existing:
            db.query(SourceFieldImport).delete()

        for record in imported_records:
            db.add(record)

        db.commit()
        return {"message": "Success", "imported_count": len(imported_records), "cleared_existing": clear_existing}
    except ValueError as ve:
        # 自定义的业务异常抛出 400，让前端明确显示
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"文件处理出现系统级异常: {str(e)}")

from sqlalchemy import func

@router.get("/source_tables/{sys_code}/{table_en}/fields")
def get_source_table_fields(sys_code: str, table_en: str, db: Session = Depends(get_db)):
    normalized_table_en = _normalize_lookup_text(table_en)
    normalized_sys_code = _normalize_lookup_text(sys_code)
    table_query = db.query(SourceFieldImport).filter(
        func.lower(func.trim(SourceFieldImport.table_en)) == normalized_table_en
    )

    records = []
    if normalized_sys_code:
        records = table_query.filter(
            func.lower(func.trim(func.coalesce(SourceFieldImport.sys_code, ""))) == normalized_sys_code
        ).all()

    if not records:
        records = table_query.all()
        
    if not records:
        return {"table_info": {}, "fields": []}
        
    table_info = {
        "sys_code": records[0].sys_code,
        "table_cn": records[0].table_cn,
        "table_en": records[0].table_en,
        "table_def": records[0].table_def,
    }
    
    # 尝试按序号排序
    try:
        records = sorted(records, key=lambda x: int(x.seq_no) if x.seq_no and x.seq_no.isdigit() else 99999)
    except:
        pass

    fields = [
        {
            "seq_no": r.seq_no,
            "field_cn": r.field_cn,
            "field_en": r.field_en,
            "field_desc": r.field_desc,
            "data_type": r.data_type,
            "length_precision": r.length_precision,
            "pk_fk": r.pk_fk,
            "is_ref_data": r.is_ref_data,
            "ref_data_desc": r.ref_data_desc,
            "ref_table_en": r.ref_table_en,
            "ref_data_usage_desc": r.ref_data_usage_desc,
        } for r in records
    ]
    return {"table_info": table_info, "fields": fields}

@router.get("/source_fields")
def get_all_source_fields(db: Session = Depends(get_db)):
    records = db.query(SourceFieldImport).order_by(SourceFieldImport.created_at.desc()).all()
    return {
        "code": 200,
        "data": records
    }

@router.post("/source_fields")
def create_source_field(field_data: SourceFieldCreate, db: Session = Depends(get_db)):
    record = SourceFieldImport(**field_data.dict())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"code": 200, "data": record}

@router.put("/source_fields/{field_id}")
def update_source_field(field_id: str, field_data: SourceFieldUpdate, db: Session = Depends(get_db)):
    record = db.query(SourceFieldImport).filter(SourceFieldImport.id == field_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Field not found")
    
    update_data = field_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)
        
    db.commit()
    db.refresh(record)
    return {"code": 200, "data": record}

@router.delete("/source_fields/{field_id}")
def delete_source_field(field_id: str, db: Session = Depends(get_db)):
    record = db.query(SourceFieldImport).filter(SourceFieldImport.id == field_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Field not found")
    
    db.delete(record)
    db.commit()
    return {"code": 200, "message": "Success"}
