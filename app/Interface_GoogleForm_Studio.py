from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import Bot_GoogleForm_Intelligent as core
from version import APP_RELEASE, APP_VERSION


COLORS = {
    "bg": "#071827",
    "panel": "#0B1F33",
    "panel_alt": "#102A43",
    "panel_card": "#0E263D",
    "input": "#0A1A2C",
    "ink": "#F4F8FC",
    "muted": "#9FB1C5",
    "accent": "#36A3FF",
    "accent_soft": "#17395C",
    "teal": "#38D6C1",
    "teal_soft": "#123F3F",
    "gold": "#F2B84B",
    "gold_soft": "#3B3218",
    "line": "#2B4865",
    "ok": "#57D68D",
    "ok_soft": "#173C2B",
    "warn": "#FF6969",
    "warn_soft": "#40202A",
    "purple": "#A970FF",
}


class ScrollZone(tk.Frame):
    def __init__(self, parent: tk.Misc, *, bg: str = COLORS["bg"], content_bg: str | None = None):
        super().__init__(parent, bg=bg)
        self.bg = bg
        self.content_bg = content_bg or bg
        self.canvas = tk.Canvas(self, bg=self.bg, bd=0, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = tk.Frame(self.canvas, bg=self.content_bg)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>", self._sync_width)
        self._bind_mousewheel()

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _sync_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _bind_mousewheel(self) -> None:
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel_linux, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel_linux, add="+")

    def _pointer_is_inside(self, event: tk.Event) -> bool:
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if widget == self:
                return True
            widget = widget.master
        return False

    def _can_scroll(self) -> bool:
        region = self.canvas.bbox("all")
        return bool(region) and region[3] > self.canvas.winfo_height()

    def _on_mousewheel(self, event: tk.Event):
        if not self._pointer_is_inside(event) or not self._can_scroll():
            return None

        if event.delta == 0:
            return "break"

        step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step, "units")
        return "break"

    def _on_mousewheel_linux(self, event: tk.Event):
        if not self._pointer_is_inside(event) or not self._can_scroll():
            return None

        step = -1 if event.num == 4 else 1
        self.canvas.yview_scroll(step, "units")
        return "break"

    def scroll_to_widget(self, widget: tk.Widget, *, padding: int = 16) -> None:
        self.update_idletasks()
        region = self.canvas.bbox("all")
        if not region:
            return

        widget_y = max(0, widget.winfo_y() - padding)
        scrollable_height = max(1, region[3] - self.canvas.winfo_height())
        self.canvas.yview_moveto(min(1.0, widget_y / scrollable_height))


class QuestionCard:
    def __init__(self, app: "GoogleFormStudioApp", parent: tk.Misc, question: dict[str, object], index: int):
        self.app = app
        self.question = question
        self.index = index
        self.validation_targets: list[tk.Widget] = []
        self.primary_input: tk.Widget | None = None
        self.error_var = tk.StringVar(value="")

        card_bg = COLORS["panel_card"]
        self.card_bg = card_bg
        self.frame = tk.Frame(
            parent,
            bg=card_bg,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            bd=0,
            padx=18,
            pady=16,
        )

        header = tk.Frame(self.frame, bg=card_bg)
        header.pack(fill="x")

        tk.Label(
            header,
            text=str(index),
            bg=COLORS["teal"],
            fg=COLORS["bg"],
            width=3,
            padx=6,
            pady=6,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left", padx=(0, 12))

        title = str(question["text"])
        if question["required"]:
            title += " *"

        self.prompt_label = tk.Label(
            header,
            text=title,
            bg=card_bg,
            fg=COLORS["ink"],
            font=("Segoe UI", 12, "bold"),
            wraplength=620,
            justify="left",
            anchor="w",
        )
        self.prompt_label.pack(side="left", fill="x", expand=True)

        tk.Label(
            self.frame,
            text=str(question["type_label"]),
            bg=card_bg,
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", padx=(54, 0), pady=(2, 6))

        self.answer_var: tk.StringVar | None = None
        self.text_widget: tk.Text | None = None
        self.checkbox_vars: dict[str, tk.BooleanVar] = {}
        self.date_vars: dict[str, tk.StringVar] = {}
        self.time_vars: dict[str, tk.StringVar] = {}
        self.grid_vars: dict[str, tk.StringVar] = {}
        self.grid_multi_vars: dict[str, dict[str, tk.BooleanVar]] = {}

        self._build_answer_zone(card_bg)
        self.error_label = tk.Label(
            self.frame,
            textvariable=self.error_var,
            bg=card_bg,
            fg=COLORS["warn"],
            font=("Segoe UI", 10, "bold"),
            wraplength=620,
            justify="left",
            anchor="w",
        )
        self.error_label.pack(fill="x", pady=(8, 0))

    def _trace_var(self, variable: tk.Variable) -> None:
        variable.trace_add("write", lambda *_args: self._on_answer_changed())

    def _on_answer_changed(self) -> None:
        self.clear_validation_error()
        self.app.refresh_summary()

    def _register_validation_target(self, widget: tk.Widget) -> tk.Widget:
        self.validation_targets.append(widget)
        if self.primary_input is None:
            self.primary_input = widget
        return widget

    def focus_input(self) -> None:
        if self.primary_input is None:
            return
        try:
            self.primary_input.focus_set()
        except tk.TclError:
            return

    def set_validation_error(self, message: str) -> None:
        self.frame.configure(highlightbackground=COLORS["warn"])
        self.prompt_label.configure(fg=COLORS["warn"])
        self.error_var.set(message)
        for widget in self.validation_targets:
            try:
                if isinstance(widget, (tk.Entry, tk.Text)):
                    widget.configure(highlightbackground=COLORS["warn"], highlightcolor=COLORS["warn"])
                else:
                    widget.configure(highlightbackground=COLORS["warn"], highlightthickness=1)
            except tk.TclError:
                continue

    def clear_validation_error(self) -> None:
        self.frame.configure(highlightbackground=COLORS["line"])
        self.prompt_label.configure(fg=COLORS["ink"])
        self.error_var.set("")
        for widget in self.validation_targets:
            try:
                if isinstance(widget, (tk.Entry, tk.Text)):
                    widget.configure(highlightbackground=COLORS["line"], highlightcolor=COLORS["teal"])
                else:
                    widget.configure(highlightbackground=COLORS["line"], highlightthickness=0)
            except tk.TclError:
                continue

    def _styled_entry(self, parent: tk.Misc, width: int = 18) -> tk.Entry:
        return tk.Entry(
            parent,
            width=width,
            relief="flat",
            bg=COLORS["input"],
            fg=COLORS["ink"],
            insertbackground=COLORS["ink"],
            font=("Segoe UI", 12),
            highlightbackground=COLORS["line"],
            highlightcolor=COLORS["teal"],
            highlightthickness=1,
        )

    def _add_labeled_entry(
        self,
        parent: tk.Misc,
        label_text: str,
        variable: tk.StringVar,
        width: int,
        column: int,
    ) -> tk.Entry:
        tk.Label(
            parent,
            text=label_text,
            bg=str(parent.cget("bg")),
            fg=COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).grid(row=0, column=column, sticky="w", padx=(0, 10))
        entry = self._styled_entry(parent, width=width)
        entry.configure(textvariable=variable)
        entry.grid(row=1, column=column, sticky="w", padx=(0, 10))
        self._register_validation_target(entry)
        return entry

    def _build_option_buttons(
        self,
        parent: tk.Misc,
        variable: tk.StringVar,
        options: list[str],
        *,
        compact: bool = False,
    ) -> None:
        for option in options:
            button = tk.Radiobutton(
                parent,
                text=option,
                variable=variable,
                value=option,
                indicatoron=0,
                relief="flat",
                selectcolor=COLORS["accent"],
                offrelief="flat",
                overrelief="flat",
                bg=COLORS["input"],
                activebackground=COLORS["accent_soft"],
                activeforeground=COLORS["ink"],
                fg=COLORS["ink"],
                padx=12,
                pady=8,
                anchor="w",
                font=("Segoe UI", 11, "bold"),
            )
            if compact:
                button.pack(side="left", padx=(0, 8), pady=4)
            else:
                button.pack(fill="x", pady=4)

    def _build_answer_zone(self, card_bg: str) -> None:
        question_type = self.question["type"]

        if self.question.get("row_labels"):
            tk.Label(
                self.frame,
                text="Lignes : " + ", ".join(self.question["row_labels"]),
                bg=card_bg,
                fg=COLORS["muted"],
                font=("Segoe UI", 10),
                anchor="w",
            ).pack(fill="x", pady=(0, 8))

        if not self.question["supported"]:
            tk.Label(
                self.frame,
                text="Ce type de question n'est pas encore pris en charge dans l'interface.",
                bg=card_bg,
                fg=COLORS["warn"],
                font=("Segoe UI", 11, "bold"),
                justify="left",
            ).pack(fill="x", pady=(8, 0))
            return

        if question_type == 0:
            self.answer_var = tk.StringVar()
            self._trace_var(self.answer_var)
            entry = self._styled_entry(self.frame, width=44)
            entry.configure(textvariable=self.answer_var)
            entry.pack(fill="x", pady=(8, 0))
            self._register_validation_target(entry)
            return

        if question_type == 1:
            box = tk.Frame(self.frame, bg=COLORS["input"], highlightbackground=COLORS["line"], highlightthickness=1)
            box.pack(fill="x", pady=(8, 0))
            text = tk.Text(
                box,
                height=4,
                relief="flat",
                bg=COLORS["input"],
                fg=COLORS["ink"],
                insertbackground=COLORS["ink"],
                font=("Segoe UI", 12),
                wrap="word",
                highlightbackground=COLORS["line"],
                highlightcolor=COLORS["teal"],
                highlightthickness=1,
            )
            text.pack(fill="both", expand=True, padx=4, pady=4)
            text.bind("<KeyRelease>", lambda _event: self._on_answer_changed())
            self._register_validation_target(text)
            self.primary_input = text
            self.text_widget = text
            return

        if question_type in {2, 3, 5}:
            self.answer_var = tk.StringVar()
            self._trace_var(self.answer_var)
            options_frame = tk.Frame(self.frame, bg=card_bg)
            options_frame.pack(fill="x", pady=(8, 0))
            self._build_option_buttons(options_frame, self.answer_var, self.question["options"])
            self._register_validation_target(options_frame)
            return

        if question_type == 4:
            options_frame = tk.Frame(self.frame, bg=card_bg)
            options_frame.pack(fill="x", pady=(8, 0))
            for option in self.question["options"]:
                variable = tk.BooleanVar(value=False)
                self._trace_var(variable)
                self.checkbox_vars[option] = variable
                tk.Checkbutton(
                    options_frame,
                    text=option,
                    variable=variable,
                    indicatoron=0,
                    relief="flat",
                    offrelief="flat",
                    overrelief="flat",
                    bg=COLORS["input"],
                    activebackground=COLORS["accent_soft"],
                    activeforeground=COLORS["ink"],
                    fg=COLORS["ink"],
                    selectcolor=COLORS["accent"],
                    padx=12,
                    pady=8,
                    anchor="w",
                    font=("Segoe UI", 11, "bold"),
                ).pack(fill="x", pady=4)
            self._register_validation_target(options_frame)
            return

        if question_type == 7:
            grid_rows = self.question.get("grid_rows") or []
            if len(grid_rows) <= 1:
                self.answer_var = tk.StringVar()
                self._trace_var(self.answer_var)
                options_frame = tk.Frame(self.frame, bg=card_bg)
                options_frame.pack(fill="x", pady=(8, 0))
                self._build_option_buttons(options_frame, self.answer_var, self.question["options"])
                self._register_validation_target(options_frame)
                return

            grid_frame = tk.Frame(self.frame, bg=card_bg)
            grid_frame.pack(fill="x", pady=(8, 0))
            for row in grid_rows:
                line = tk.Frame(grid_frame, bg=card_bg)
                line.pack(fill="x", pady=(0, 10))
                tk.Label(
                    line,
                    text=row["label"],
                    bg=card_bg,
                    fg=COLORS["ink"],
                    font=("Segoe UI", 11, "bold"),
                    anchor="w",
                ).pack(fill="x")

                variable = tk.StringVar()
                self._trace_var(variable)
                self.grid_vars[row["field_name"]] = variable

                options_line = tk.Frame(line, bg=card_bg)
                options_line.pack(fill="x", pady=(6, 0))
                self._build_option_buttons(options_line, variable, self.question["options"], compact=True)
            self._register_validation_target(grid_frame)
            return

        if question_type == 8:
            grid_frame = tk.Frame(self.frame, bg=card_bg)
            grid_frame.pack(fill="x", pady=(8, 0))
            for row in self.question.get("grid_rows") or []:
                line = tk.Frame(grid_frame, bg=card_bg)
                line.pack(fill="x", pady=(0, 10))
                tk.Label(
                    line,
                    text=row["label"],
                    bg=card_bg,
                    fg=COLORS["ink"],
                    font=("Segoe UI", 11, "bold"),
                    anchor="w",
                ).pack(fill="x")

                options_line = tk.Frame(line, bg=card_bg)
                options_line.pack(fill="x", pady=(6, 0))
                row_vars: dict[str, tk.BooleanVar] = {}
                for option in self.question["options"]:
                    variable = tk.BooleanVar(value=False)
                    self._trace_var(variable)
                    row_vars[option] = variable
                    tk.Checkbutton(
                        options_line,
                        text=option,
                        variable=variable,
                        indicatoron=0,
                        relief="flat",
                        offrelief="flat",
                        overrelief="flat",
                        bg=COLORS["input"],
                        activebackground=COLORS["accent_soft"],
                        activeforeground=COLORS["ink"],
                        fg=COLORS["ink"],
                        selectcolor=COLORS["accent"],
                        padx=12,
                        pady=8,
                        anchor="w",
                        font=("Segoe UI", 10, "bold"),
                    ).pack(side="left", padx=(0, 8), pady=4)
                self.grid_multi_vars[row["field_name"]] = row_vars
            self._register_validation_target(grid_frame)
            return

        if question_type == 9:
            form = tk.Frame(self.frame, bg=card_bg)
            form.pack(fill="x", pady=(8, 0))

            self.date_vars["day"] = tk.StringVar()
            self.date_vars["month"] = tk.StringVar()
            self._trace_var(self.date_vars["day"])
            self._trace_var(self.date_vars["month"])

            self._add_labeled_entry(form, "JJ", self.date_vars["day"], 8, 0)
            self._add_labeled_entry(form, "MM", self.date_vars["month"], 8, 1)

            if self.question.get("includes_year"):
                self.date_vars["year"] = tk.StringVar()
                self._trace_var(self.date_vars["year"])
                self._add_labeled_entry(form, "AAAA", self.date_vars["year"], 12, 2)

            tk.Label(
                self.frame,
                text="Format : JJ/MM/AAAA" if self.question.get("includes_year") else "Format : JJ/MM",
                bg=card_bg,
                fg=COLORS["muted"],
                font=("Segoe UI", 10),
                anchor="w",
            ).pack(fill="x", pady=(8, 0))
            return

        if question_type == 10:
            form = tk.Frame(self.frame, bg=card_bg)
            form.pack(fill="x", pady=(8, 0))

            self.time_vars["hour"] = tk.StringVar()
            self.time_vars["minute"] = tk.StringVar()
            self._trace_var(self.time_vars["hour"])
            self._trace_var(self.time_vars["minute"])

            self._add_labeled_entry(form, "HH", self.time_vars["hour"], 8, 0)
            self._add_labeled_entry(form, "MM", self.time_vars["minute"], 8, 1)

            tk.Label(
                self.frame,
                text="Format : HH:MM",
                bg=card_bg,
                fg=COLORS["muted"],
                font=("Segoe UI", 10),
                anchor="w",
            ).pack(fill="x", pady=(8, 0))

    def _required_message(self) -> str:
        return f"La question '{self.question['text']}' est obligatoire."

    def _missing(self, default, strict: bool, message: str | None = None):
        if strict and self.question["required"]:
            raise ValueError(message or self._required_message())
        return default

    def read_answer(self, strict: bool = False):
        if not self.question["supported"]:
            if strict and self.question["required"]:
                raise ValueError(f"Question non prise en charge : {self.question['text']}")
            return "__UNSUPPORTED__"

        question_type = self.question["type"]

        if question_type == 0:
            value = self.answer_var.get().strip()
            return value or self._missing(None, strict)

        if question_type == 1:
            value = self.text_widget.get("1.0", "end").strip()
            return value or self._missing(None, strict)

        if question_type in {2, 3, 5}:
            value = self.answer_var.get().strip()
            return value or self._missing(None, strict)

        if question_type == 4:
            selected = [option for option, variable in self.checkbox_vars.items() if variable.get()]
            return selected or self._missing([], strict)

        if question_type == 7:
            grid_rows = self.question.get("grid_rows") or []
            if len(grid_rows) <= 1:
                value = self.answer_var.get().strip()
                return value or self._missing(None, strict)

            rows = []
            missing_count = 0
            for row in grid_rows:
                value = self.grid_vars[row["field_name"]].get().strip()
                if value:
                    rows.append(
                        {
                            "field_name": row["field_name"],
                            "label": row["label"],
                            "value": value,
                        }
                    )
                else:
                    missing_count += 1

            if rows and not missing_count:
                return core.build_grid_answer(rows)
            if rows and not self.question["required"]:
                return core.build_grid_answer(rows)
            return self._missing(None, strict, f"La grille '{self.question['text']}' est incomplete.")

        if question_type == 8:
            rows = []
            has_any_value = False
            for row in self.question.get("grid_rows") or []:
                values = [
                    option
                    for option, variable in self.grid_multi_vars[row["field_name"]].items()
                    if variable.get()
                ]
                rows.append({"field_name": row["field_name"], "label": row["label"], "values": values})
                has_any_value = has_any_value or bool(values)

            if all(row["values"] for row in rows):
                return core.build_grid_multi_answer(rows)
            if has_any_value and not self.question["required"]:
                return core.build_grid_multi_answer(rows)
            return self._missing(None, strict, f"La grille '{self.question['text']}' est incomplete.")

        if question_type == 9:
            day = self.date_vars["day"].get().strip()
            month = self.date_vars["month"].get().strip()
            year_value = self.date_vars.get("year").get().strip() if self.date_vars.get("year") else ""
            if not any([day, month, year_value]):
                return self._missing(None, strict)
            raw_date = f"{day}/{month}/{year_value}" if self.question.get("includes_year") else f"{day}/{month}"
            try:
                return core.parse_date_input(raw_date, bool(self.question.get("includes_year")))
            except ValueError as error:
                if strict:
                    raise ValueError(f"{self.question['text']} : {error}") from error
                return None

        if question_type == 10:
            hour = self.time_vars["hour"].get().strip()
            minute = self.time_vars["minute"].get().strip()
            if not any([hour, minute]):
                return self._missing(None, strict)
            try:
                return core.parse_time_input(f"{hour}:{minute}")
            except ValueError as error:
                if strict:
                    raise ValueError(f"{self.question['text']} : {error}") from error
                return None

        return "__UNSUPPORTED__"

    def preview_text(self) -> str:
        answer = self.read_answer(strict=False)
        if answer == "__UNSUPPORTED__":
            return "(non pris en charge)"
        return core.format_answer_for_summary(self.question, answer)

    def set_answer(self, answer) -> None:
        question_type = self.question["type"]

        if question_type == 0 and self.answer_var is not None:
            self.answer_var.set("" if answer is None else str(answer))
        elif question_type == 1 and self.text_widget is not None:
            self.text_widget.delete("1.0", "end")
            if answer:
                self.text_widget.insert("1.0", str(answer))
        elif question_type in {2, 3, 5} and self.answer_var is not None:
            self.answer_var.set("" if answer is None else str(answer))
        elif question_type == 4:
            selected = set(answer or [])
            for option, variable in self.checkbox_vars.items():
                variable.set(option in selected)
        elif question_type == 7:
            if self.grid_vars and isinstance(answer, dict) and answer.get("__grid__"):
                values = {row["field_name"]: row["value"] for row in answer.get("rows", [])}
                for field_name, variable in self.grid_vars.items():
                    variable.set(values.get(field_name, ""))
            elif self.answer_var is not None:
                self.answer_var.set("" if answer is None else str(answer))
        elif question_type == 8 and isinstance(answer, dict) and answer.get("__grid_multi__"):
            values_by_row = {row["field_name"]: set(row.get("values", [])) for row in answer.get("rows", [])}
            for field_name, option_vars in self.grid_multi_vars.items():
                selected = values_by_row.get(field_name, set())
                for option, variable in option_vars.items():
                    variable.set(option in selected)
        elif question_type == 9 and isinstance(answer, dict):
            self.date_vars["day"].set(answer.get("day", "") or "")
            self.date_vars["month"].set(answer.get("month", "") or "")
            if self.date_vars.get("year") is not None:
                self.date_vars["year"].set(answer.get("year", "") or "")
        elif question_type == 10 and isinstance(answer, dict):
            self.time_vars["hour"].set(answer.get("hour", "") or "")
            self.time_vars["minute"].set(answer.get("minute", "") or "")

    def set_random_answer(self, profile: str) -> None:
        if self.question["supported"]:
            answer = core.generate_random_answer(self.question, profile)
            if answer != "__UNSUPPORTED__":
                self.set_answer(answer)

    def clear_answer(self) -> None:
        if self.answer_var is not None:
            self.answer_var.set("")
        if self.text_widget is not None:
            self.text_widget.delete("1.0", "end")
        for variable in self.checkbox_vars.values():
            variable.set(False)
        for variable in self.date_vars.values():
            variable.set("")
        for variable in self.time_vars.values():
            variable.set("")
        for variable in self.grid_vars.values():
            variable.set("")
        for row_vars in self.grid_multi_vars.values():
            for variable in row_vars.values():
                variable.set(False)


class GoogleFormStudioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_RELEASE)
        self.root.configure(bg=COLORS["bg"])
        self._configure_window()
        self._configure_icon()

        self.form_data: dict[str, object] | None = None
        self.cards: list[QuestionCard] = []
        self.busy = False
        self.batch_stop_event = threading.Event()
        self.batch_pause_event = threading.Event()
        self.batch_is_running = False
        self.batch_is_paused = False
        self.batch_stop_requested = False
        self.batch_snapshot: dict[str, object] | None = None
        self.current_batch_action_label = "Envoyees"

        self.url_var = tk.StringVar()
        self.meta_var = tk.StringVar(value="Aucun formulaire charge.")
        self.stats_var = tk.StringVar(value="0 question")
        self.status_var = tk.StringVar(value="Pret pour analyser un formulaire public.")
        self.progress_var = tk.StringVar(value="Aucune serie en cours.")

        self.auto_count_var = tk.StringVar(value="5")
        self.auto_min_delay_var = tk.StringVar(value="0.4")
        self.auto_max_delay_var = tk.StringVar(value="1.2")
        self.auto_retry_var = tk.StringVar(value="2")
        self.auto_profile_var = tk.StringVar(value="equilibre")
        self.auto_simulate_var = tk.BooleanVar(value=False)

        self.controlled_widgets: list[tk.Widget] = []

        self._build_ui()
        self.reset_form()
        self.refresh_logs()

    def _configure_window(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(1380, max(960, screen_width - 80))
        height = min(900, max(680, screen_height - 120))
        offset_x = max(20, (screen_width - width) // 2)
        offset_y = max(20, (screen_height - height) // 3)
        self.root.geometry(f"{width}x{height}+{offset_x}+{offset_y}")
        self.root.minsize(min(width, 960), min(height, 680))

    def _configure_icon(self) -> None:
        icon_path = core.ASSET_DIR / "app-icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

    def _build_ui(self) -> None:
        self._configure_progress_style()

        body = tk.Frame(self.root, bg=COLORS["bg"], padx=6, pady=6)
        body.pack(fill="both", expand=True)

        controls = tk.Frame(
            body,
            bg=COLORS["panel"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=20,
            pady=20,
            width=340,
        )
        controls.pack(side="left", fill="y", padx=(0, 4))
        controls.pack_propagate(False)
        controls_scroll = ScrollZone(controls, bg=COLORS["panel"], content_bg=COLORS["panel"])
        controls_scroll.pack(fill="both", expand=True)
        controls_content = controls_scroll.content

        canvas_panel = tk.Frame(
            body,
            bg=COLORS["panel"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=20,
            pady=20,
        )
        canvas_panel.pack(side="left", fill="both", expand=True, padx=(0, 4))

        summary_panel = tk.Frame(
            body,
            bg=COLORS["panel"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=20,
            pady=20,
            width=390,
        )
        summary_panel.pack(side="right", fill="y")
        summary_panel.pack_propagate(False)

        brand = tk.Frame(controls_content, bg=COLORS["panel"])
        brand.pack(fill="x", pady=(0, 18))
        self.logo_image = None
        logo_path = core.ASSET_DIR / "app-icon.png"
        if logo_path.exists():
            try:
                self.logo_image = tk.PhotoImage(file=str(logo_path)).subsample(4, 4)
                tk.Label(brand, image=self.logo_image, bg=COLORS["panel"]).pack(side="left", padx=(0, 12))
            except tk.TclError:
                self.logo_image = None

        title_box = tk.Frame(brand, bg=COLORS["panel"])
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_box,
            text="Google Form",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=("Segoe UI", 20, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_box,
            text="Studio",
            bg=COLORS["panel"],
            fg=COLORS["teal"],
            font=("Segoe UI", 20, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            controls_content,
            text="1. Lien du Google Form",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x")

        self.url_entry = tk.Entry(
            controls_content,
            textvariable=self.url_var,
            relief="flat",
            bg=COLORS["input"],
            fg=COLORS["ink"],
            insertbackground=COLORS["ink"],
            font=("Segoe UI", 12),
            highlightbackground=COLORS["line"],
            highlightcolor=COLORS["teal"],
            highlightthickness=1,
        )
        self.url_entry.pack(fill="x")

        self.analyze_button = self._make_button(
            controls_content,
            text="Analyser le formulaire",
            bg=COLORS["teal"],
            fg=COLORS["bg"],
            command=self.analyze_form,
        )
        self.analyze_button.pack(fill="x", pady=(12, 16))

        self.status_box = tk.Frame(controls_content, bg=COLORS["teal_soft"], padx=12, pady=12)
        self.status_box.pack(fill="x")
        self.status_heading = tk.Label(
            self.status_box,
            text="Etat",
            bg=COLORS["teal_soft"],
            fg=COLORS["ink"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        )
        self.status_heading.pack(fill="x")
        self.status_label = tk.Label(
            self.status_box,
            textvariable=self.status_var,
            bg=COLORS["teal_soft"],
            fg=COLORS["ink"],
            font=("Segoe UI", 10, "bold"),
            wraplength=260,
            justify="left",
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(8, 0))

        tk.Label(
            controls_content,
            textvariable=self.meta_var,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=280,
            anchor="w",
        ).pack(fill="x", pady=(16, 16))

        actions_box = tk.Frame(controls_content, bg=COLORS["panel"])
        actions_box.pack(fill="x")
        tk.Label(
            actions_box,
            text="2. Actions rapides",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        self.random_button = self._make_button(
            actions_box,
            text="Generer les reponses (IA)",
            bg=COLORS["accent_soft"],
            command=self.fill_random_answers,
        )
        self.random_button.pack(fill="x", pady=(0, 10))

        self.clear_button = self._make_button(
            actions_box,
            text="Vider les reponses",
            bg=COLORS["panel_alt"],
            command=self.clear_answers,
        )
        self.clear_button.pack(fill="x", pady=(0, 10))

        self.simulate_button = self._make_button(
            actions_box,
            text="Simuler sans envoyer",
            bg=COLORS["accent_soft"],
            command=self.simulate_current_answers,
        )
        self.simulate_button.pack(fill="x", pady=(0, 10))

        self.submit_button = self._make_button(
            actions_box,
            text="Envoyer la reponse",
            bg=COLORS["ok_soft"],
            fg=COLORS["ink"],
            command=self.submit_answers,
        )
        self.submit_button.pack(fill="x", pady=(0, 16))

        auto_box = tk.Frame(controls_content, bg=COLORS["panel"], padx=0, pady=0)
        auto_box.pack(fill="x", pady=(0, 16))

        tk.Label(
            auto_box,
            text="3. Automatisation",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        self._labeled_control(auto_box, "Nombre de reponses")
        self.auto_count_entry = self._make_entry(auto_box, self.auto_count_var)
        self.auto_count_entry.pack(fill="x", pady=(4, 8))

        self._labeled_control(auto_box, "Profil")
        profile_menu = tk.OptionMenu(auto_box, self.auto_profile_var, *core.AUTO_PROFILES)
        profile_menu.configure(
            relief="flat",
            bg=COLORS["input"],
            fg=COLORS["ink"],
            activebackground=COLORS["input"],
            activeforeground=COLORS["ink"],
            highlightthickness=1,
            highlightbackground=COLORS["line"],
            font=("Segoe UI", 11),
        )
        profile_menu["menu"].configure(bg=COLORS["input"], fg=COLORS["ink"], font=("Segoe UI", 11))
        profile_menu.pack(fill="x", pady=(4, 8))
        self.auto_profile_menu = profile_menu

        delays_row = tk.Frame(auto_box, bg=COLORS["panel"])
        delays_row.pack(fill="x", pady=(0, 8))
        tk.Label(
            delays_row,
            text="Delais min / max (s)",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x")
        delay_inputs = tk.Frame(delays_row, bg=COLORS["panel"])
        delay_inputs.pack(fill="x", pady=(4, 0))
        self.auto_min_delay_entry = self._make_entry(delay_inputs, self.auto_min_delay_var, width=8)
        self.auto_min_delay_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.auto_max_delay_entry = self._make_entry(delay_inputs, self.auto_max_delay_var, width=8)
        self.auto_max_delay_entry.pack(side="left", fill="x", expand=True)

        self._labeled_control(auto_box, "Retries auto par reponse")
        self.auto_retry_entry = self._make_entry(auto_box, self.auto_retry_var)
        self.auto_retry_entry.pack(fill="x", pady=(4, 8))

        self.auto_simulate_check = tk.Checkbutton(
            auto_box,
            text="Simulation uniquement",
            variable=self.auto_simulate_var,
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["ink"],
            selectcolor=COLORS["input"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            relief="flat",
        )
        self.auto_simulate_check.pack(fill="x", pady=(4, 10))

        self.auto_button = self._make_button(
            auto_box,
            text="Lancer la serie",
            bg=COLORS["ok_soft"],
            fg=COLORS["ink"],
            command=self.send_random_series,
        )
        self.auto_button.pack(fill="x", pady=(0, 8))

        self.pause_button = self._make_button(
            auto_box,
            text="Mettre en pause",
            bg=COLORS["gold_soft"],
            command=self.toggle_batch_pause,
        )
        self.pause_button.pack(fill="x", pady=(0, 8))

        self.stop_button = self._make_button(
            auto_box,
            text="Arreter la serie",
            bg=COLORS["warn_soft"],
            fg=COLORS["ink"],
            command=self.request_stop_batch,
        )
        self.stop_button.pack(fill="x")

        progress_box = tk.Frame(auto_box, bg=COLORS["panel"])
        progress_box.pack(fill="x", pady=(12, 0))
        tk.Label(
            progress_box,
            textvariable=self.progress_var,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
            wraplength=280,
            justify="left",
            anchor="w",
        ).pack(fill="x")
        self.progress_bar = ttk.Progressbar(progress_box, mode="determinate", maximum=100)
        self.progress_bar.configure(style="Codex.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(6, 0))

        footer_box = tk.Frame(controls_content, bg=COLORS["panel"])
        footer_box.pack(fill="x", pady=(16, 0))

        self.refresh_logs_button = self._make_button(
            footer_box,
            text="Actualiser l'historique",
            bg=COLORS["panel_alt"],
            command=self.refresh_logs,
        )
        self.refresh_logs_button.pack(fill="x", pady=(0, 10))

        self.clear_history_button = self._make_button(
            footer_box,
            text="Effacer l'historique local",
            bg=COLORS["panel_alt"],
            command=self.clear_local_history,
        )
        self.clear_history_button.pack(fill="x", pady=(0, 10))

        self.reset_button = self._make_button(
            footer_box,
            text="Reinitialiser",
            bg=COLORS["panel_alt"],
            command=self.reset_form,
        )
        self.reset_button.pack(fill="x", pady=(0, 10))

        self.controlled_widgets.extend(
            [
                self.random_button,
                self.clear_button,
                self.simulate_button,
                self.submit_button,
                self.auto_count_entry,
                self.auto_profile_menu,
                self.auto_min_delay_entry,
                self.auto_max_delay_entry,
                self.auto_retry_entry,
                self.auto_button,
                self.auto_simulate_check,
            ]
        )

        tabs = tk.Frame(canvas_panel, bg=COLORS["panel"])
        tabs.pack(fill="x", pady=(0, 12))
        tk.Label(
            tabs,
            text="Questions",
            bg=COLORS["accent_soft"],
            fg=COLORS["teal"],
            font=("Segoe UI", 11, "bold"),
            padx=22,
            pady=10,
        ).pack(side="left", padx=(0, 12))
        for tab_name in ("Simulation", "Reponse brute (JSON)"):
            tk.Label(
                tabs,
                text=tab_name,
                bg=COLORS["panel"],
                fg=COLORS["muted"],
                font=("Segoe UI", 11),
                padx=22,
                pady=10,
            ).pack(side="left")

        tk.Label(
            canvas_panel,
            text="Remplissez ou generez les reponses ci-dessous",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=("Segoe UI", 11),
            anchor="w",
        ).pack(fill="x")

        self.scroll_zone = ScrollZone(canvas_panel, bg=COLORS["panel"], content_bg=COLORS["panel"])
        self.scroll_zone.pack(fill="both", expand=True, pady=(14, 0))

        tk.Label(
            summary_panel,
            text="Recapitulatif",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            summary_panel,
            textvariable=self.stats_var,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 12))

        self.summary_text = tk.Text(
            summary_panel,
            relief="flat",
            bg=COLORS["input"],
            fg=COLORS["ink"],
            font=("Segoe UI", 11),
            wrap="word",
            padx=12,
            pady=12,
            state="disabled",
            height=18,
        )
        self.summary_text.pack(fill="both", expand=True)

        tk.Label(
            summary_panel,
            text="Journal recent",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(16, 8))

        self.log_text = tk.Text(
            summary_panel,
            relief="flat",
            bg=COLORS["input"],
            fg=COLORS["ink"],
            font=("Segoe UI", 10),
            wrap="word",
            padx=12,
            pady=12,
            state="disabled",
            height=12,
        )
        self.log_text.pack(fill="both", expand=False)

    def _configure_progress_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("default")
        except tk.TclError:
            pass
        style.configure(
            "Codex.Horizontal.TProgressbar",
            troughcolor="white",
            background=COLORS["teal"],
            bordercolor=COLORS["line"],
            lightcolor=COLORS["teal"],
            darkcolor=COLORS["teal"],
        )

    def _make_entry(self, parent: tk.Misc, variable: tk.StringVar, width: int = 12) -> tk.Entry:
        entry = tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            relief="flat",
            bg=COLORS["input"],
            fg=COLORS["ink"],
            insertbackground=COLORS["ink"],
            font=("Segoe UI", 12),
            highlightbackground=COLORS["line"],
            highlightcolor=COLORS["teal"],
            highlightthickness=1,
        )
        return entry

    def _labeled_control(self, parent: tk.Misc, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            bg=str(parent.cget("bg")),
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x")

    def _make_button(
        self,
        parent: tk.Misc,
        text: str,
        bg: str,
        command,
        fg: str = "white",
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=10,
            cursor="hand2",
        )

    def _clear_questions(self) -> None:
        for child in self.scroll_zone.content.winfo_children():
            child.destroy()

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in self.controlled_widgets:
            widget.configure(state=state)

    def _write_summary(self, text: str) -> None:
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state="disabled")

    def _write_logs(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", text)
        self.log_text.configure(state="disabled")

    def _set_running(self, running: bool, *, keep_controls_disabled: bool | None = None) -> None:
        self.busy = running
        self.analyze_button.configure(state="disabled" if running else "normal")
        if keep_controls_disabled is None:
            keep_controls_disabled = running or not self.form_data
        self._set_controls_enabled(not keep_controls_disabled)

    def _set_batch_running(self, running: bool) -> None:
        self.batch_is_running = running
        self.pause_button.configure(state="normal" if running else "disabled")
        self.stop_button.configure(state="normal" if running else "disabled")
        if not running:
            self.batch_stop_event.clear()
            self.batch_pause_event.clear()
            self.batch_is_paused = False
            self.batch_stop_requested = False
            self.pause_button.configure(text="Mettre en pause")

    def _format_batch_progress(self, snapshot: dict[str, object], *, stopped: bool = False) -> str:
        count = int(snapshot.get("count", snapshot.get("requested_count", 0)))
        pending_count = int(snapshot.get("pending_count", 0))
        parts = [
            f"Traitees : {snapshot['processed_count']} / {count}",
            f"{self.current_batch_action_label} : {snapshot['success_count']}",
            f"En attente : {pending_count}",
            f"Erreurs : {snapshot['error_count']}",
            f"Retries : {snapshot.get('retry_count_total', 0)}",
        ]
        if pending_count > 0:
            eta_text = "pause" if self.batch_is_paused else core.format_duration_compact(snapshot.get("eta_seconds"))
            parts.append(f"Reste estime : {eta_text}")
        if stopped:
            parts.append("serie arretee")
        elif self.batch_stop_requested:
            parts.append("arret demande")
        elif self.batch_is_paused:
            parts.append("pause")
        return " | ".join(parts)

    def _render_batch_progress(self, *, stopped: bool = False) -> None:
        if self.batch_snapshot is None:
            self.progress_var.set("Aucune serie en cours.")
            return
        self.progress_var.set(self._format_batch_progress(self.batch_snapshot, stopped=stopped))

    def _focus_first_invalid_card(self) -> None:
        for card in self.cards:
            if card.error_var.get():
                self.scroll_zone.scroll_to_widget(card.frame)
                card.focus_input()
                break

    def set_status(self, text: str, tone: str) -> None:
        if tone == "ok":
            bg, fg = COLORS["ok_soft"], COLORS["ok"]
        elif tone == "warn":
            bg, fg = COLORS["warn_soft"], COLORS["warn"]
        elif tone == "busy":
            bg, fg = COLORS["gold_soft"], COLORS["ink"]
        else:
            bg, fg = COLORS["teal_soft"], COLORS["ink"]

        self.status_var.set(text)
        self.status_box.configure(bg=bg)
        self.status_heading.configure(bg=bg, fg=fg)
        self.status_label.configure(bg=bg, fg=fg)

    def run_task(self, worker, callback) -> None:
        def wrapped() -> None:
            result = None
            error = None
            try:
                result = worker()
            except Exception as exc:  # pragma: no cover - UI background wrapper
                error = str(exc)
            self.root.after(0, lambda: callback(result, error))

        threading.Thread(target=wrapped, daemon=True).start()

    def refresh_logs(self) -> None:
        entries = core.read_recent_logs(18)
        if not entries:
            self._write_logs("Aucune activite recente.")
            return
        self._write_logs("\n".join(core.format_log_entry(entry) for entry in entries))

    def clear_local_history(self) -> None:
        if not messagebox.askyesno(
            "Effacer l'historique local",
            "Supprimer le journal local et les derniers snapshots de ce PC ?",
        ):
            return

        deleted_count = core.clear_local_history()
        self.refresh_logs()
        self.set_status("Historique local efface.", "ok")
        messagebox.showinfo(
            "Historique local efface",
            f"{deleted_count} fichier(s) local(aux) supprime(s).",
        )

    def show_report_dialog(self, title: str, content: str) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("840x620")
        dialog.configure(bg=COLORS["panel"])
        dialog.transient(self.root)

        text = tk.Text(
            dialog,
            relief="flat",
            bg=COLORS["input"],
            fg=COLORS["ink"],
            font=("Menlo", 11),
            wrap="word",
            padx=12,
            pady=12,
        )
        text.insert("1.0", content)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Button(
            dialog,
            text="Fermer",
            command=dialog.destroy,
            relief="flat",
            bg=COLORS["ink"],
            fg="white",
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=10,
            cursor="hand2",
        ).pack(pady=(0, 18))

    def analyze_form(self) -> None:
        if self.busy:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Lien manquant", "Colle d'abord un lien de Google Form.")
            return

        self._set_running(True)
        self.set_status("Analyse en cours...", "busy")
        self.meta_var.set("Recuperation des questions...")
        self._write_summary("Chargement du formulaire...")

        def worker():
            return core.parse_form(url)

        def callback(result, error) -> None:
            self._set_running(False, keep_controls_disabled=not bool(result and result["questions"]))
            self.refresh_logs()
            if error:
                self.reset_form()
                self.url_var.set(url)
                self.set_status(f"Analyse impossible : {error}", "warn")
                messagebox.showerror("Analyse impossible", error)
                return
            self.form_data = result
            self.populate_questions()

        self.run_task(worker, callback)

    def populate_questions(self) -> None:
        self.cards = []
        self._clear_questions()

        if not self.form_data or not self.form_data["questions"]:
            self._write_summary("Aucune question exploitable n'a ete detectee.")
            self.stats_var.set("0 question")
            self.meta_var.set("Aucun formulaire charge.")
            self.set_status("Aucune question exploitable n'a ete detectee.", "warn")
            self._set_controls_enabled(False)
            return

        for index, question in enumerate(self.form_data["questions"], start=1):
            card = QuestionCard(self, self.scroll_zone.content, question, index)
            card.frame.pack(fill="x", pady=(0, 14))
            self.cards.append(card)

        total = len(self.form_data["questions"])
        supported = sum(1 for question in self.form_data["questions"] if question["supported"])
        unsupported_required = sum(
            1
            for question in self.form_data["questions"]
            if question["required"] and not question["supported"]
        )

        self.meta_var.set(f"{self.form_data['title']} | {total} question(s) | {supported} prises en charge")
        self._set_controls_enabled(True)
        self.refresh_summary()

        if unsupported_required:
            self.set_status(
                f"Formulaire charge avec {unsupported_required} question(s) obligatoire(s) non geree(s).",
                "warn",
            )
        else:
            self.set_status(f"Formulaire charge : {total} question(s).", "ok")

    def build_summary_text(self) -> str:
        if not self.cards:
            self.stats_var.set("0 question")
            return "Analyse un formulaire pour voir le recap ici."

        answers: dict[str, object] = {}
        ready_count = 0
        questions = []

        for card in self.cards:
            questions.append(card.question)
            answer = card.read_answer(strict=False)
            if answer != "__UNSUPPORTED__":
                answers[card.question["field_name"]] = answer
            if answer != "__UNSUPPORTED__" and not core.is_blank_answer(answer):
                ready_count += 1

        self.stats_var.set(f"{len(self.cards)} question(s)  |  {ready_count} deja remplies")
        return core.build_summary_text(questions, answers)

    def refresh_summary(self) -> None:
        self._write_summary(self.build_summary_text())

    def collect_answers(self, strict: bool = False, *, highlight_invalid: bool = False) -> dict[str, object]:
        if not self.form_data:
            raise ValueError("Analyse d'abord un formulaire.")

        answers: dict[str, object] = {}
        errors: list[str] = []

        if highlight_invalid:
            for card in self.cards:
                card.clear_validation_error()

        for card in self.cards:
            try:
                answer = card.read_answer(strict=strict)
            except ValueError as error:
                errors.append(str(error))
                if highlight_invalid:
                    card.set_validation_error(str(error))
                continue

            if answer == "__UNSUPPORTED__":
                continue
            if not core.is_blank_answer(answer):
                answers[card.question["field_name"]] = answer

        if errors:
            if highlight_invalid:
                self._focus_first_invalid_card()
            raise ValueError("Corrige les champs en rouge :\n- " + "\n- ".join(errors))

        return answers

    def clear_answers(self) -> None:
        for card in self.cards:
            card.clear_answer()
            card.clear_validation_error()
        self.refresh_summary()
        self.set_status("Les champs ont ete vides.", "neutral")

    def fill_random_answers(self) -> None:
        profile = self.auto_profile_var.get()
        for card in self.cards:
            card.set_random_answer(profile)
            card.clear_validation_error()
        self.refresh_summary()
        self.set_status(f"Les champs ont ete remplis avec le profil {profile}.", "ok")

    def _current_summary_text(self, answers: dict[str, object]) -> str:
        return core.build_summary_text(self.form_data["questions"], answers)

    def simulate_current_answers(self) -> None:
        if self.busy:
            return

        try:
            answers = self.collect_answers(strict=True, highlight_invalid=True)
        except ValueError as error:
            messagebox.showerror("Simulation impossible", str(error))
            self.set_status("Correction necessaire avant simulation.", "warn")
            return

        simulation = core.simulate_submission(self.form_data, answers, label="simulation interface")
        self._write_summary(simulation["summary_text"])
        self.refresh_logs()
        self.set_status("Simulation preparee sans envoi.", "ok")
        self.show_report_dialog("Simulation de la reponse", core.format_simulation_report(simulation))

    def submit_answers(self) -> None:
        if self.busy:
            return

        try:
            answers = self.collect_answers(strict=True, highlight_invalid=True)
        except ValueError as error:
            messagebox.showerror("Verification impossible", str(error))
            self.set_status("Correction necessaire avant envoi.", "warn")
            return

        if not messagebox.askyesno(
            "Confirmer l'envoi",
            "Envoyer cette reponse ?\n\nLe recapitulatif affiche sera utilise.",
        ):
            self.set_status("Envoi annule.", "neutral")
            return

        self._set_running(True)
        self.set_status("Envoi en cours...", "busy")
        self._write_summary(self._current_summary_text(answers))

        def worker():
            core.submit_form(self.form_data, answers)

        def callback(_result, error) -> None:
            self._set_running(False, keep_controls_disabled=not bool(self.form_data))
            self.refresh_logs()
            if error:
                self.set_status(f"Envoi refuse : {error}", "warn")
                messagebox.showerror("Echec de l'envoi", error)
                return
            self.set_status("Reponse envoyee avec succes.", "ok")
            messagebox.showinfo("Envoi termine", "La reponse a ete envoyee.")

        self.run_task(worker, callback)

    def request_stop_batch(self) -> None:
        if not self.batch_is_running:
            return
        self.batch_stop_requested = True
        self.batch_stop_event.set()
        self.pause_button.configure(state="disabled")
        self.set_status("Arret demande pour la serie automatique...", "warn")
        self._render_batch_progress()

    def toggle_batch_pause(self) -> None:
        if not self.batch_is_running or self.batch_stop_requested:
            return

        if self.batch_pause_event.is_set():
            self.batch_pause_event.clear()
            self.batch_is_paused = False
            self.pause_button.configure(text="Mettre en pause")
            self.set_status("Serie automatique reprise.", "busy")
        else:
            self.batch_pause_event.set()
            self.batch_is_paused = True
            self.pause_button.configure(text="Reprendre la serie")
            self.set_status("Serie automatique en pause.", "warn")

        self._render_batch_progress()

    def _read_auto_options(self) -> tuple[int, str, float, float, int, bool]:
        count = core.parse_positive_integer(self.auto_count_var.get())
        profile = core.parse_profile(self.auto_profile_var.get())
        min_delay = core.parse_delay_value(self.auto_min_delay_var.get())
        max_delay = core.parse_delay_value(self.auto_max_delay_var.get())
        max_retries = core.parse_non_negative_integer(self.auto_retry_var.get())
        core.validate_delay_range(min_delay, max_delay)
        simulate_only = bool(self.auto_simulate_var.get())
        return count, profile, min_delay, max_delay, max_retries, simulate_only

    def send_random_series(self) -> None:
        if self.busy:
            return
        if not self.form_data:
            messagebox.showerror("Formulaire manquant", "Analyse d'abord un formulaire.")
            return

        try:
            count, profile, min_delay, max_delay, max_retries, simulate_only = self._read_auto_options()
        except ValueError as error:
            messagebox.showerror("Options invalides", str(error))
            return

        sample_answers = core.collect_random_answers(self.form_data["questions"], profile)
        if sample_answers is None:
            messagebox.showerror(
                "Serie impossible",
                "Certaines questions obligatoires ne sont pas gerees pour le mode automatique.",
            )
            return

        action_label = "simuler" if simulate_only else "envoyer"
        if not messagebox.askyesno(
            "Confirmer la serie",
            f"Voulez-vous {action_label} {count} reponse(s) avec le profil {profile} ?",
        ):
            self.set_status("Serie automatique annulee.", "neutral")
            return

        self.batch_stop_event.clear()
        self.batch_pause_event.clear()
        self.batch_is_paused = False
        self.batch_stop_requested = False
        self._set_running(True)
        self._set_batch_running(True)
        self.progress_bar.configure(style="Codex.Horizontal.TProgressbar")
        self.progress_bar["value"] = 0
        self.current_batch_action_label = "Simulees" if simulate_only else "Envoyees"
        self.batch_snapshot = {
            "count": count,
            "processed_count": 0,
            "pending_count": count,
            "success_count": 0,
            "error_count": 0,
            "retry_count_total": 0,
            "eta_seconds": None,
        }
        self.pause_button.configure(text="Mettre en pause")
        self._render_batch_progress()
        self.set_status("Serie automatique en cours...", "busy")
        self._write_summary(core.build_summary_text(self.form_data["questions"], sample_answers))

        def on_progress(payload: dict[str, object]) -> None:
            def update_ui() -> None:
                self.batch_snapshot = payload
                progress_value = (payload["processed_count"] / payload["count"]) * 100
                self.progress_bar["value"] = progress_value
                self._render_batch_progress()

            self.root.after(0, update_ui)

        def worker():
            return core.run_random_submissions(
                self.form_data,
                count,
                profile=profile,
                min_delay=min_delay,
                max_delay=max_delay,
                simulate_only=simulate_only,
                max_retries=max_retries,
                on_progress=on_progress,
                stop_requested=self.batch_stop_event.is_set,
                pause_requested=self.batch_pause_event.is_set,
            )

        def callback(result, error) -> None:
            self._set_batch_running(False)
            self._set_running(False, keep_controls_disabled=not bool(self.form_data))
            self.refresh_logs()

            if error:
                self.progress_var.set("Serie interrompue par une erreur.")
                self.set_status(f"Serie interrompue : {error}", "warn")
                messagebox.showerror("Serie interrompue", error)
                return

            self.batch_snapshot = result
            success_count = result["success_count"]
            error_count = result["error_count"]
            stopped = result["stopped"]
            self.progress_bar["value"] = (
                100
                if result["requested_count"] == 0
                else (result["processed_count"] / result["requested_count"]) * 100
            )
            self._render_batch_progress(stopped=stopped)
            self.set_status(
                f"Mode automatique termine : {success_count} succes, {error_count} erreur(s), "
                f"{result['retry_count_total']} retry(s)."
                + (" Serie arretee." if stopped else ""),
                "ok" if error_count == 0 and not stopped else "warn",
            )

            if stopped:
                messagebox.showinfo(
                    "Serie arretee",
                    f"Serie stoppee proprement.\n{success_count} succes, {error_count} erreur(s).",
                )
                return

            if error_count:
                details = f"\nDerniere erreur : {result['last_error']}" if result["last_error"] else ""
                messagebox.showwarning(
                    "Serie terminee",
                    f"{success_count} succes, {error_count} erreur(s).{details}",
                )
            else:
                messagebox.showinfo(
                    "Serie terminee",
                    f"{success_count} {self.current_batch_action_label.lower()} terminees avec succes.",
                )

        self.run_task(worker, callback)

    def reset_form(self) -> None:
        self.form_data = None
        self.cards = []
        self.batch_snapshot = None
        self.current_batch_action_label = "Envoyees"
        self.url_var.set("")
        self._clear_questions()

        tk.Label(
            self.scroll_zone.content,
            text="Analyse un formulaire pour afficher ici les cartes de questions.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 13, "bold"),
            pady=40,
        ).pack(fill="x")

        self.meta_var.set("Aucun formulaire charge.")
        self.stats_var.set("0 question")
        self.progress_var.set("Aucune serie en cours.")
        self.progress_bar["value"] = 0
        self._write_summary("Analyse un formulaire pour voir le recap ici.")
        self._set_batch_running(False)
        self._set_running(False, keep_controls_disabled=True)
        self.set_status("Pret pour une nouvelle analyse.", "neutral")
        self.refresh_logs()
        self.url_entry.focus_set()


def main() -> None:
    root = tk.Tk()
    GoogleFormStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

