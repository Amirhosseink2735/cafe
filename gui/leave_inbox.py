"""Admin leave inbox: filters, approve, and reject with comments."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from gui.style import COLORS, app_font, center_window
from services.leave_service import (
    FILTER_MAP,
    STATUS_APPROVED,
    STATUS_LABELS,
    STATUS_PENDING,
    STATUS_REJECTED,
    LeaveRequestRecord,
    LeaveService,
)


class LeaveDecisionDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, confirm_text: str) -> None:
        super().__init__(master)
        self.comment = ""
        self.confirmed = False
        self.title(title)
        self.configure(fg_color=COLORS["cream"])
        self.resizable(False, False)
        self.transient(master)
        center_window(self, 480, 340)
        self.grab_set()

        card = ctk.CTkFrame(self, corner_radius=20, fg_color=COLORS["card"])
        card.pack(expand=True, fill="both", padx=18, pady=18)

        ctk.CTkLabel(
            card, text=title, font=app_font(18, "bold"), text_color=COLORS["espresso"]
        ).pack(pady=(16, 8))
        ctk.CTkLabel(
            card, text="توضیحات مدیر", font=app_font(13), anchor="e"
        ).pack(fill="x", padx=20)
        self.box = ctk.CTkTextbox(card, height=110, font=app_font(14))
        self.box.pack(fill="x", padx=20, pady=(4, 8))
        self.error_label = ctk.CTkLabel(
            card, text="", font=app_font(12), text_color=COLORS["danger"]
        )
        self.error_label.pack()
        ctk.CTkButton(
            card,
            text=confirm_text,
            height=42,
            command=self._confirm,
        ).pack(fill="x", padx=20, pady=(8, 18))
        self.after(80, self.box.focus_set)

    def _confirm(self) -> None:
        text = self.box.get("1.0", "end").strip()
        if not text:
            self.error_label.configure(text="توضیحات مدیر را وارد کنید.")
            return
        self.comment = text
        self.confirmed = True
        self.destroy()


class LeaveInboxFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        leave_service: LeaveService,
        on_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.leave_service = leave_service
        self.on_changed = on_changed
        self.filter_var = ctk.StringVar(value=STATUS_LABELS[STATUS_PENDING])

        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            heading,
            text="کارتابل مرخصی‌ها",
            font=app_font(22, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(side="right")
        self.pending_badge = ctk.CTkLabel(
            heading,
            text="",
            font=app_font(13, "bold"),
            text_color=COLORS["espresso"],
        )
        self.pending_badge.pack(side="left")

        self.filter_bar = ctk.CTkSegmentedButton(
            self,
            values=list(FILTER_MAP.keys()),
            variable=self.filter_var,
            font=app_font(13, "bold"),
            height=40,
            command=lambda _value: self.refresh(),
        )
        self.filter_bar.pack(fill="x", pady=(0, 12))

        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=18, fg_color=COLORS["card"])
        self.list_frame.pack(expand=True, fill="both")
        self.refresh()

    def refresh(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()

        pending = self.leave_service.pending_count()
        self.pending_badge.configure(
            text=f"{pending} درخواست در انتظار بررسی" if pending else "درخواست معوقی نیست"
        )

        status = FILTER_MAP.get(self.filter_var.get())
        requests = self.leave_service.list_requests(status)
        if not requests:
            ctk.CTkLabel(
                self.list_frame,
                text="موردی با این فیلتر پیدا نشد.",
                font=app_font(15),
                text_color=COLORS["muted"],
            ).pack(pady=40)
            return

        for item in requests:
            self._add_card(item)

        if self.on_changed:
            self.on_changed()

    def _add_card(self, item: LeaveRequestRecord) -> None:
        colors = {
            STATUS_PENDING: (COLORS["pill_off_bg"], COLORS["pill_off_fg"]),
            STATUS_APPROVED: (COLORS["pill_ok_bg"], COLORS["pill_ok_fg"]),
            STATUS_REJECTED: ("#F3E6E3", COLORS["danger"]),
        }
        pill_bg, pill_fg = colors.get(item.status, (COLORS["ghost"], COLORS["ink"]))

        card = ctk.CTkFrame(self.list_frame, corner_radius=16, fg_color=COLORS["cream"])
        card.pack(fill="x", padx=10, pady=8)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 6))
        ctk.CTkLabel(
            top,
            text=item.employee_name,
            font=app_font(16, "bold"),
            text_color=COLORS["ink"],
            anchor="e",
        ).pack(side="right")
        pill = ctk.CTkFrame(top, fg_color=pill_bg, corner_radius=12, width=130, height=28)
        pill.pack(side="left")
        pill.pack_propagate(False)
        ctk.CTkLabel(
            pill, text=item.status_label, font=app_font(12, "bold"), text_color=pill_fg
        ).pack(expand=True)

        ctk.CTkLabel(
            card,
            text=f"کد {item.personnel_code}  ·  {item.type_label}  ·  {item.period_label}",
            font=app_font(13),
            text_color=COLORS["muted"],
            anchor="e",
        ).pack(fill="x", padx=14)
        ctk.CTkLabel(
            card,
            text=f"دلیل پرسنل: {item.reason}",
            font=app_font(13),
            text_color=COLORS["espresso"],
            anchor="e",
            wraplength=900,
        ).pack(fill="x", padx=14, pady=(4, 4))
        if item.admin_comment:
            ctk.CTkLabel(
                card,
                text=f"توضیح مدیر: {item.admin_comment}",
                font=app_font(12),
                text_color=COLORS["muted"],
                anchor="e",
                wraplength=900,
            ).pack(fill="x", padx=14)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(6, 14))
        if item.status == STATUS_PENDING:
            ctk.CTkButton(
                actions,
                text="تایید مرخصی",
                width=130,
                height=34,
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                command=lambda req_id=item.id: self._decide(req_id, approve=True),
            ).pack(side="right", padx=(6, 0))
            ctk.CTkButton(
                actions,
                text="رد مرخصی",
                width=130,
                height=34,
                fg_color=COLORS["danger"],
                hover_color=COLORS["danger_hover"],
                command=lambda req_id=item.id: self._decide(req_id, approve=False),
            ).pack(side="right")
        elif item.reviewed_at:
            ctk.CTkLabel(
                actions,
                text=f"بررسی شده در {item.reviewed_at}",
                font=app_font(11),
                text_color=COLORS["muted"],
                anchor="w",
            ).pack(side="left")

    def _decide(self, request_id: int, approve: bool) -> None:
        title = "تایید مرخصی" if approve else "رد مرخصی"
        dialog = LeaveDecisionDialog(self.winfo_toplevel(), title, title)
        self.wait_window(dialog)
        if not getattr(dialog, "confirmed", False):
            return
        try:
            if approve:
                self.leave_service.approve(request_id, dialog.comment)
            else:
                self.leave_service.reject(request_id, dialog.comment)
        except ValueError as exc:
            self.pending_badge.configure(text=str(exc))
            return
        self.refresh()
