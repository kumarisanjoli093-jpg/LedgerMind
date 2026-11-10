# backend/api_transactions.py
from fastapi import APIRouter, HTTPException
from typing import List
from .schemas import TransactionCreate
from .db import get_connection

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

@router.post("/", status_code=201)
def create_transaction(tx: TransactionCreate):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions 
            (user_id, receipt_id, vendor, gstin, invoice_number, invoice_date, 
             taxable_amount, cgst, sgst, igst, total_tax, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tx.user_id, tx.receipt_id, tx.vendor, tx.gstin, tx.invoice_number, 
              tx.invoice_date, tx.taxable_amount, tx.cgst, tx.sgst, tx.igst, 
              tx.total_tax, tx.total_amount))
        conn.commit()
        tx_id = cursor.lastrowid
        return {"message": "Transaction created successfully", "id": tx_id}

@router.get("/")
def get_transactions():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.put("/{tx_id}")
def update_transaction(tx_id: int, tx: TransactionCreate):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE transactions SET 
                vendor=?, gstin=?, invoice_number=?, invoice_date=?, 
                taxable_amount=?, cgst=?, sgst=?, igst=?, 
                total_tax=?, total_amount=?
            WHERE id=?
        """, (tx.vendor, tx.gstin, tx.invoice_number, tx.invoice_date, 
              tx.taxable_amount, tx.cgst, tx.sgst, tx.igst, 
              tx.total_tax, tx.total_amount, tx_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")
        conn.commit()
        return {"message": "Transaction updated successfully"}

@router.delete("/{tx_id}")
def delete_transaction(tx_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")
        conn.commit()
        return {"message": "Transaction deleted successfully"}