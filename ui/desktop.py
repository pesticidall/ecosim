from pathlib import Path
from calendar import monthrange
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from core.content_catalog import build_content_registry
from core.content_loader import load_json_file
from simulation.scenario_loader import load_scenario
from ui.controller import SimulationController
from ui.history import HISTORY_CATEGORIES
from simulation.interventions import (
    supplementary_food_options, preview_supplementary_food,
    preview_population_removal, preview_population_introduction, MAX_POPULATION_ACTION_QUANTITY,
)
from simulation.intervention_resources import (
    FeedType, MAX_IC, HERBIVORE_STOCK_CAPACITY_KG, CARNIVORE_STOCK_CAPACITY_KG,
)


class EcoSimApp:
    """Minimal desktop shell; scheduling and drawing never resolve ecology."""

    SPEEDS = {"Slow": 1000, "Normal": 300, "Fast": 50}

    def __init__(self, root: tk.Tk, project_root: Path):
        self.root = root
        self.controller = None
        self._scheduled = None
        self._locations = {}
        self.registry = build_content_registry(project_root / "content")
        self.scenarios = sorted((project_root / "scenarios").glob("*.json"))
        if not self.scenarios:
            raise ValueError("No scenarios are available.")
        root.title("EcoSim · Playtest B")
        root.geometry("1180x760")
        root.minsize(980, 620)
        root.configure(bg="#10241e")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#10241e")
        style.configure("TLabel", background="#10241e", foreground="#dce9dc", font=("Segoe UI", 11))
        style.configure("Title.TLabel", font=("Segoe UI", 26, "bold"), foreground="#c3df92")
        style.configure("Heading.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Calendar.TButton", font=("Segoe UI", 9), padding=1)
        style.configure("Treeview", background="#19382d", fieldbackground="#19382d", foreground="#e2eddf",
                        rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#45684a")])
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        header = ttk.Frame(root, padding=(22, 16))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="EcoSim", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.date_text = tk.StringVar()
        ttk.Label(header, textvariable=self.date_text, style="Heading.TLabel").grid(row=0, column=1, sticky="e")
        self.budget_text = tk.StringVar()
        ttk.Label(header, textvariable=self.budget_text).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        toolbar = ttk.Frame(root, padding=(22, 0, 22, 14))
        toolbar.grid(row=1, column=0, sticky="ew")
        self.scenario = ttk.Combobox(toolbar, state="readonly", width=31,
                                     values=[load_json_file(path)["name"] for path in self.scenarios])
        self.scenario.current(0)
        self.scenario.grid(row=0, column=0, padx=(0, 8))
        self.load_button = ttk.Button(toolbar, text="Load scenario", command=self._load)
        self.load_button.grid(row=0, column=1, padx=(0, 12))
        self.day_button = ttk.Button(toolbar, text="Next day", command=self._step)
        self.day_button.grid(row=0, column=2, padx=3)
        self.play_button = ttk.Button(toolbar, text="Play month", command=self._play)
        self.play_button.grid(row=0, column=3, padx=3)
        self.pause_button = ttk.Button(toolbar, text="Pause", command=self._pause)
        self.pause_button.grid(row=0, column=4, padx=3)
        self.speed = ttk.Combobox(toolbar, state="readonly", width=8, values=list(self.SPEEDS))
        self.speed.set("Slow")
        self.speed.grid(row=0, column=5, padx=8)
        self.review_button = ttk.Button(toolbar, text="Finish review", command=self._review)
        self.review_button.grid(row=0, column=6, padx=3)
        body = ttk.Frame(root, padding=(22, 0, 22, 12))
        body.grid(row=2, column=0, sticky="nsew")
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=3)
        body.columnconfigure(2, weight=3)
        for column, title in enumerate(("HABITATS", "LOCAL ECOLOGY", "FIELD NOTES / MONTHLY REVIEW")):
            ttk.Label(body, text=title, style="Heading.TLabel").grid(row=0, column=column, sticky="w", pady=(0, 10))
        self.habitats = ttk.Treeview(body, show="tree", selectmode="browse", height=14)
        self.habitats.column("#0", width=205, minwidth=160)
        self.habitats.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        self.habitats.bind("<<TreeviewSelect>>", lambda _event: self._render_local())
        middle = ttk.Frame(body)
        middle.grid(row=1, column=1, sticky="nsew", padx=(0, 14))
        middle.columnconfigure(0, weight=1)
        middle.rowconfigure(1, weight=2)
        middle.rowconfigure(3, weight=1)
        self.location_text = tk.StringVar()
        ttk.Label(middle, textvariable=self.location_text, wraplength=310).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.species = self._table(middle, ("Species", "Population", "Injured"), (155, 85, 65))
        self.species.grid(row=1, column=0, sticky="nsew")
        ttk.Label(middle, text="RESOURCES", style="Heading.TLabel").grid(row=2, column=0, sticky="w", pady=(18, 8))
        self.resources = self._table(middle, ("Resource", "Available"), (175, 130))
        self.resources.grid(row=3, column=0, sticky="nsew")
        food = ttk.Frame(middle, padding=(0, 12, 0, 0))
        food.grid(row=4, column=0, sticky="ew")
        food.columnconfigure(0, weight=1)
        ttk.Label(food, text="SUPPLEMENTARY FOOD", style="Heading.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        self.food_resource = ttk.Combobox(food, state="readonly", width=18)
        self.food_resource.grid(row=1, column=0, sticky="ew", pady=7, padx=(0, 6))
        self.food_amount = tk.StringVar(value="50")
        self.food_quantity = ttk.Spinbox(food, from_=50, to=HERBIVORE_STOCK_CAPACITY_KG, increment=50,
                                        textvariable=self.food_amount, width=7, state="readonly")
        self.food_quantity.grid(row=1, column=1, padx=(0, 4))
        ttk.Label(food, text="kg").grid(row=1, column=2)
        self.food_button = ttk.Button(food, text="Add food", command=self._add_food)
        self.food_button.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.food_date = tk.StringVar()
        ttk.Label(food, textvariable=self.food_date, wraplength=310).grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))
        self._food_options = {}
        self.food_preview = tk.StringVar()
        ttk.Label(food, textvariable=self.food_preview, wraplength=310).grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.food_resource.bind("<<ComboboxSelected>>", lambda _event: self._update_food_preview())
        self.food_amount.trace_add("write", lambda *_args: self._update_food_preview())
        self.notes_tabs = ttk.Notebook(body)
        self.notes_tabs.grid(row=1, column=2, sticky="nsew")
        notes = ttk.Frame(self.notes_tabs)
        history = ttk.Frame(self.notes_tabs)
        self.notes_tabs.add(notes, text="Latest notes / review")
        self.notes_tabs.add(history, text="History")
        for panel in (notes, history):
            panel.columnconfigure(0, weight=1)
            panel.rowconfigure(1, weight=1)
        self.report = ScrolledText(notes, wrap="word", width=39, bg="#19382d", fg="#e2eddf",
                                   insertbackground="#e2eddf", relief="flat", padx=14, pady=14,
                                   font=("Segoe UI", 10), state="disabled")
        self.report.grid(row=1, column=0, sticky="nsew")
        self.history_choice = tk.StringVar(value="Latest completed day")
        self.history_selector = ttk.Combobox(history, state="readonly", textvariable=self.history_choice, width=35)
        self.history_selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.history_selector.bind("<<ComboboxSelected>>", lambda _event: self._render_history())
        self.history_report = ScrolledText(history, wrap="word", width=39, bg="#19382d", fg="#e2eddf",
                                           relief="flat", padx=14, pady=14, font=("Segoe UI", 10), state="disabled")
        self.history_report.grid(row=1, column=0, sticky="nsew")
        intervention_panel = ttk.Frame(self.notes_tabs, padding=14)
        self.notes_tabs.add(intervention_panel, text="Interventions")
        intervention_panel.columnconfigure(0, weight=1)
        action_tabs = ttk.Notebook(intervention_panel)
        action_tabs.grid(row=0, column=0, sticky="nsew")
        intervention_panel.rowconfigure(0, weight=1)
        removal_panel = ttk.Frame(action_tabs, padding=8)
        introduction_panel = ttk.Frame(action_tabs, padding=8)
        action_tabs.add(removal_panel, text="Remove")
        action_tabs.add(introduction_panel, text="Introduce")
        removal_panel.columnconfigure(0, weight=1)
        introduction_panel.columnconfigure(0, weight=1)
        ttk.Label(removal_panel, text="REMOVE 1–10 ANIMALS", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        self.removal_availability = tk.StringVar()
        ttk.Label(removal_panel, textvariable=self.removal_availability, wraplength=330).grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.removal_species = ttk.Combobox(removal_panel, state="readonly", width=32)
        self.removal_species.grid(row=3, column=0, sticky="ew")
        self.removal_species.bind("<<ComboboxSelected>>", lambda _event: self._update_removal_preview())
        self.removal_amount = tk.StringVar(value="1")
        self.removal_quantity = ttk.Spinbox(removal_panel, from_=1, to=MAX_POPULATION_ACTION_QUANTITY,
                                          increment=1, textvariable=self.removal_amount, width=8)
        self.removal_quantity.grid(row=4, column=0, sticky="w", pady=2)
        self.removal_preview = tk.StringVar()
        ttk.Label(removal_panel, textvariable=self.removal_preview, wraplength=330).grid(row=5, column=0, sticky="w", pady=2)
        self.removal_button = ttk.Button(removal_panel, text="Remove animals · 3 IC", command=self._remove_animals)
        self.removal_button.grid(row=6, column=0, sticky="ew")
        self._removal_options = {}
        self.removal_amount.trace_add("write", lambda *_args: self._update_removal_preview())
        ttk.Label(introduction_panel, text="POPULATION INTRODUCTION", style="Heading.TLabel").grid(row=0, column=0, sticky="w", pady=(16, 8))
        self.introduction_species = ttk.Combobox(introduction_panel, state="readonly", width=32)
        self.introduction_species.grid(row=1, column=0, sticky="ew")
        self.introduction_species.bind("<<ComboboxSelected>>", lambda _event: self._update_introduction_preview())
        self.introduction_amount = tk.StringVar(value="1")
        self.introduction_quantity = ttk.Spinbox(introduction_panel, from_=1, to=MAX_POPULATION_ACTION_QUANTITY,
                                               increment=1, textvariable=self.introduction_amount, width=8)
        self.introduction_quantity.grid(row=2, column=0, sticky="w", pady=6)
        self.introduction_preview = tk.StringVar()
        ttk.Label(introduction_panel, textvariable=self.introduction_preview, wraplength=330).grid(row=3, column=0, sticky="w", pady=6)
        self.introduction_button = ttk.Button(introduction_panel, text="Introduce animals · 4 IC", command=self._introduce_animals)
        self.introduction_button.grid(row=4, column=0, sticky="ew")
        self._introduction_options = {}
        self.introduction_amount.trace_add("write", lambda *_args: self._update_introduction_preview())
        calendar_panel = ttk.Frame(self.notes_tabs, padding=8)
        self.notes_tabs.add(calendar_panel, text="Calendar")
        calendar_panel.columnconfigure(0, weight=1)
        calendar_panel.rowconfigure(3, weight=1)
        calendar_controls = ttk.Frame(calendar_panel)
        calendar_controls.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        calendar_controls.columnconfigure(0, weight=3)
        calendar_controls.columnconfigure(1, weight=2)
        self.calendar_choice = tk.StringVar(value="Current month / review")
        self.calendar_selector = ttk.Combobox(calendar_controls, state="readonly", textvariable=self.calendar_choice, width=18)
        self.calendar_selector.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.calendar_selector.bind("<<ComboboxSelected>>", lambda _event: self._change_calendar_month())
        self.calendar_category = tk.StringVar(value="All events")
        self.calendar_filter = ttk.Combobox(calendar_controls, state="readonly", textvariable=self.calendar_category,
                                           values=HISTORY_CATEGORIES, width=13)
        self.calendar_filter.grid(row=0, column=1, sticky="ew")
        self.calendar_filter.bind("<<ComboboxSelected>>", lambda _event: self._render_calendar_detail())
        self.calendar_grid = ttk.Frame(calendar_panel)
        self.calendar_grid.grid(row=1, column=0, sticky="ew")
        self.calendar_legend = ttk.Label(calendar_panel, text="D = completed · N = unresolved · + = intervention",
                                         wraplength=330)
        self.calendar_legend.grid(row=2, column=0, sticky="w", pady=2)
        self.calendar_report = ScrolledText(calendar_panel, wrap="word", width=39, height=5,
                                            bg="#19382d", fg="#e2eddf", relief="flat", padx=10, pady=10,
                                            font=("Segoe UI", 10), state="disabled")
        self.calendar_report.grid(row=3, column=0, sticky="nsew")
        self._calendar_date = None
        self._calendar_month_options = {}
        self._calendar_buttons = {}
        self.status_text = tk.StringVar()
        ttk.Label(root, textvariable=self.status_text, padding=(22, 8, 22, 14)).grid(row=3, column=0, sticky="ew")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._load()

    def _table(self, parent, columns, widths):
        table = ttk.Treeview(parent, columns=columns, show="headings", height=5)
        for column, width in zip(columns, widths):
            table.heading(column, text=column)
            table.column(column, width=width, minwidth=50, anchor="w" if column == columns[0] else "e")
        return table

    def _load(self):
        self._pause()
        try:
            world = load_scenario(self.scenarios[self.scenario.current()], self.registry)
        except (ValueError, KeyError, OSError) as error:
            messagebox.showerror("Could not load scenario", str(error), parent=self.root)
            return
        self.controller = SimulationController(world, self.registry)
        self.history_choice.set("Latest completed day")
        self.calendar_choice.set("Current month / review")
        self.calendar_category.set("All events")
        self._calendar_date = None
        self.habitats.delete(*self.habitats.get_children())
        self._locations.clear()
        for region_id, region in sorted(world.regions.items()):
            parent = self.habitats.insert("", "end", text=self.registry.get(region_id)["name"], open=True)
            for habitat_id in sorted(region.habitats):
                item = self.habitats.insert(parent, "end", text=self.registry.get(habitat_id)["name"])
                self._locations[item] = (region_id, habitat_id)
        if self._locations:
            populated = next((item for item, (region_id, habitat_id) in self._locations.items()
                              if any(world.regions[region_id].habitats[habitat_id].animal_populations.values())),
                             next(iter(self._locations)))
            self.habitats.selection_set(populated)
        self.refresh()

    def _action(self, operation):
        try:
            operation()
        except Exception as error:
            self._pause()
            messagebox.showerror("Simulation stopped", str(error), parent=self.root)
        self.refresh()

    def _step(self):
        self._action(self.controller.step_day)

    def _play(self):
        self._action(self.controller.play_month)
        if self.controller.running and self._scheduled is None:
            self._scheduled = self.root.after(self.SPEEDS[self.speed.get()], self._tick)

    def _tick(self):
        self._scheduled = None
        self._action(self.controller.tick)
        if self.controller.running:
            self._scheduled = self.root.after(self.SPEEDS[self.speed.get()], self._tick)

    def _pause(self):
        if self._scheduled is not None:
            self.root.after_cancel(self._scheduled)
            self._scheduled = None
        if self.controller is not None:
            self.controller.pause()
            self.refresh()

    def _review(self):
        self._action(self.controller.acknowledge_review)

    def _add_food(self):
        selected = self.habitats.selection()
        if not selected or selected[0] not in self._locations:
            return
        region_id, habitat_id = self._locations[selected[0]]
        self._action(lambda: self.controller.add_food(
            region_id, habitat_id, self._food_options[self.food_resource.get()], float(self.food_amount.get()),
        ))
        self.notes_tabs.select(0)

    def _remove_animals(self):
        selected = self.habitats.selection()
        if not selected or selected[0] not in self._locations or self.removal_species.get() not in self._removal_options:
            return
        region_id, habitat_id = self._locations[selected[0]]
        self._action(lambda: self.controller.remove_animals(region_id, habitat_id,
                     self._removal_options[self.removal_species.get()], int(self.removal_amount.get())))
        self.notes_tabs.select(0)

    def _introduce_animals(self):
        selected = self.habitats.selection()
        if not selected or selected[0] not in self._locations or self.introduction_species.get() not in self._introduction_options:
            return
        region_id, habitat_id = self._locations[selected[0]]
        self._action(lambda: self.controller.introduce_animals(region_id, habitat_id,
                     self._introduction_options[self.introduction_species.get()], int(self.introduction_amount.get())))
        self.notes_tabs.select(0)

    def refresh(self):
        world = self.controller.world
        date = world.calendar
        self.date_text.set(f"Year {date.year}  ·  {date.day} {date.month.display_name}")
        budget = world.intervention_resources
        self.budget_text.set(f"IC {budget.ic:g}/{MAX_IC:g}  ·  Herbivore feed {budget.herbivore_stock_kg:g}/"
                             f"{HERBIVORE_STOCK_CAPACITY_KG:g} kg  ·  Carnivore feed {budget.carnivore_stock_kg:g}/"
                             f"{CARNIVORE_STOCK_CAPACITY_KG:g} kg")
        review = world.pending_month_review is not None
        running = self.controller.running
        self.day_button.configure(state="disabled" if running or review else "normal")
        self.play_button.configure(state="disabled" if running or review else "normal")
        self.pause_button.configure(state="normal" if running else "disabled")
        self.review_button.configure(state="normal" if review else "disabled")
        self.load_button.configure(state="disabled" if running else "normal")
        self.scenario.configure(state="disabled" if running else "readonly")
        self.status_text.set("Month complete · review the report before continuing." if review else
                             "Running · pause between any two dates." if running else
                             f"Paused · next unresolved date shown above · {world.scenario_name} · seed {world.random_seed}")
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", self.controller.report_text)
        self.report.configure(state="disabled")
        self._render_local()
        self._render_history()
        self._render_calendar()

    def _change_calendar_month(self):
        self._calendar_date = None
        self._render_calendar()

    def _render_calendar(self):
        world = self.controller.world
        self._calendar_month_options = {f"{month.display_name}, Year {year}": (year, month)
                                        for year, month in self.controller.calendar_months()}
        self.calendar_selector.configure(values=["Current month / review", *self._calendar_month_options])
        if self.calendar_choice.get() not in ("Current month / review", *self._calendar_month_options):
            self.calendar_choice.set("Current month / review")
        year, month = self._calendar_month_options.get(
            self.calendar_choice.get(), world.pending_month_review or (world.calendar.year, world.calendar.month))
        days = self.controller.calendar_days(year, month)
        if self._calendar_date is None or self._calendar_date[:2] != (year, month):
            preferred = world.calendar.day if (year, month) == (world.calendar.year, world.calendar.month) else len(days)
            self._calendar_date = (year, month, preferred)
        for child in self.calendar_grid.winfo_children():
            child.destroy()
        self._calendar_buttons = {}
        for column, label in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            self.calendar_grid.columnconfigure(column, weight=1, uniform="calendar")
            ttk.Label(self.calendar_grid, text=label, anchor="center").grid(row=0, column=column, sticky="ew")
        offset = monthrange(year, month.value)[0]
        for entry in days:
            row, column = divmod(offset + entry.day - 1, 7)
            marker = "D" if entry.status == "Completed" else "N" if entry.status == "Current" else ""
            text = f"{entry.day}{marker}{'+' if entry.intervention_count else ''}"
            button = ttk.Button(self.calendar_grid, text=text, width=3, style="Calendar.TButton",
                                command=lambda date=(year, month, entry.day): self._select_calendar_day(date))
            button.grid(row=row + 1, column=column, sticky="ew", padx=1, pady=1)
            if self._calendar_date == (year, month, entry.day):
                button.state(["pressed"])
            self._calendar_buttons[entry.day] = button
        self._render_calendar_detail()

    def _select_calendar_day(self, date):
        self._calendar_date = date
        for day, button in self._calendar_buttons.items():
            button.state(["pressed"] if day == date[2] else ["!pressed"])
        self._render_calendar_detail()

    def _render_calendar_detail(self):
        text = self.controller.calendar_day_text(*self._calendar_date, category=self.calendar_category.get())
        if self.calendar_report.get("1.0", "end-1c") != text:
            self.calendar_report.configure(state="normal")
            self.calendar_report.delete("1.0", "end")
            self.calendar_report.insert("1.0", text)
            self.calendar_report.configure(state="disabled")

    def _render_history(self):
        entries = {entry.label: entry for entry in self.controller.history_entries()}
        self.history_selector.configure(values=["Latest completed day", *entries])
        if self.history_choice.get() not in ("Latest completed day", *entries):
            self.history_choice.set("Latest completed day")
        text = self.controller.history_text(entries.get(self.history_choice.get()))
        if self.history_report.get("1.0", "end-1c") != text:
            self.history_report.configure(state="normal")
            self.history_report.delete("1.0", "end")
            self.history_report.insert("1.0", text)
            self.history_report.configure(state="disabled")

    def _render_local(self):
        selected = self.habitats.selection()
        if not selected or selected[0] not in self._locations:
            self.food_button.configure(state="disabled")
            self.removal_button.configure(state="disabled")
            self.introduction_button.configure(state="disabled")
            return
        region_id, habitat_id = self._locations[selected[0]]
        region = self.controller.world.regions[region_id]
        habitat = region.habitats[habitat_id]
        self._removal_options = {self.registry.get(animal_id)["name"]: animal_id
                                 for animal_id, count in sorted(habitat.animal_populations.items()) if count > 0}
        self.removal_species.configure(values=list(self._removal_options))
        if self.removal_species.get() not in self._removal_options:
            self.removal_species.set(next(iter(self._removal_options), ""))
        self._update_removal_preview()
        self._introduction_options = {definition["name"]: definition["id"]
                                      for definition in self.registry.definitions_of_type("animal")
                                      if habitat_id in definition.get("preferred_habitat_ids", ())}
        self.introduction_species.configure(values=list(self._introduction_options))
        if self.introduction_species.get() not in self._introduction_options:
            self.introduction_species.set(next(iter(self._introduction_options), ""))
        self._update_introduction_preview()
        self._food_options = {
            self.registry.get(resource_id)["name"]: resource_id for resource_id in supplementary_food_options(
                self.controller.world, self.registry, region_id, habitat_id,
            )
        }
        self.food_resource.configure(values=list(self._food_options))
        if self.food_resource.get() not in self._food_options:
            self.food_resource.set(next(iter(self._food_options), ""))
        self._update_food_preview()
        date = self.controller.world.calendar
        self.food_date.set(f"Applies on {date.day} {date.month.display_name}, Year {date.year}. "
                           + ("Pause to add food." if self.controller.running else ""))
        weather = self.registry.get(region.active_weather_id)["name"] if region.active_weather_id else "Unspecified"
        carrion = sum(deposit.available_biomass_kg for deposit in habitat.carrion_deposits)
        self.location_text.set(f"{self.registry.get(habitat_id)['name']}\n{weather} · {carrion:.2f} kg carrion")
        self.species.delete(*self.species.get_children())
        for animal_id, count in sorted(habitat.animal_populations.items()):
            injured = sum(cohort.count for cohort in habitat.injury_cohorts.get(animal_id, ()))
            self.species.insert("", "end", values=(self.registry.get(animal_id)["name"], count, injured))
        self.resources.delete(*self.resources.get_children())
        for resource_id, amount in sorted(habitat.resource_quantities.items()):
            definition = self.registry.get(resource_id)
            self.resources.insert("", "end", values=(definition["name"], f"{amount:.2f} {definition['unit']}"))

    def _update_food_preview(self):
        selected = self.habitats.selection()
        if self.controller is None or not selected or selected[0] not in self._locations or self.food_resource.get() not in self._food_options:
            self.food_preview.set("Select a populated habitat and compatible feed.")
            self.food_button.configure(state="disabled")
            return
        region_id, habitat_id = self._locations[selected[0]]
        resource_id = self._food_options[self.food_resource.get()]
        meat = self.registry.get(resource_id)["supplementary_feed_type"] == FeedType.CARNIVORE.value
        self.food_quantity.configure(to=CARNIVORE_STOCK_CAPACITY_KG if meat else HERBIVORE_STOCK_CAPACITY_KG)
        try:
            quote = preview_supplementary_food(self.controller.world, self.registry, region_id, habitat_id,
                                              resource_id, float(self.food_amount.get()))
        except (TypeError, ValueError) as error:
            self.food_preview.set(str(error))
            self.food_button.configure(state="disabled")
            return
        stock = quote.resources_after.carnivore_stock_kg if meat else quote.resources_after.herbivore_stock_kg
        self.food_preview.set(f"Cost: {quote.ic_cost:g} IC · after: {quote.resources_after.ic:g} IC\n"
                              f"{quote.feed_type.value.title()} reserve after: {stock:g} kg")
        self.food_button.configure(state="disabled" if self.controller.running else "normal")

    def _update_removal_preview(self):
        cooldown = self.controller.world.intervention_resources.removal_cooldown_months
        self.removal_availability.set(f"Charge recovering: {cooldown} monthly completion(s) remaining." if cooldown
                                       else "1 charge ready · cost 3 IC · recovery 2 months")
        selected = self.habitats.selection()
        if not selected or selected[0] not in self._locations or self.removal_species.get() not in self._removal_options:
            self.removal_preview.set("Select a populated habitat and a species.")
            self.removal_button.configure(state="disabled")
            return
        region_id, habitat_id = self._locations[selected[0]]
        animal_id = self._removal_options[self.removal_species.get()]
        population = self.controller.world.regions[region_id].habitats[habitat_id].animal_populations[animal_id]
        self.removal_quantity.configure(to=min(MAX_POPULATION_ACTION_QUANTITY, population))
        date = self.controller.world.calendar
        target = (f"{self.registry.get(habitat_id)['name']} · {date.day} {date.month.display_name}, Year {date.year}\n"
                  f"Quantity: {self.removal_amount.get()} {self.removal_species.get()} · cost 3 IC\n")
        try:
            quote = preview_population_removal(self.controller.world, self.registry, region_id, habitat_id,
                                               animal_id, int(self.removal_amount.get()))
        except (ValueError, TypeError) as error:
            self.removal_preview.set(target + str(error))
            self.removal_button.configure(state="disabled")
            return
        self.removal_preview.set(target + f"Local population: {quote.local_before} → {quote.local_after}\n"
                                 f"IC after: {quote.resources_after.ic:g}" + ("\nPause before applying." if self.controller.running else ""))
        self.removal_button.configure(state="disabled" if self.controller.running else "normal")

    def _update_introduction_preview(self):
        selected = self.habitats.selection()
        if self.controller is None or not selected or selected[0] not in self._locations or self.introduction_species.get() not in self._introduction_options:
            self.introduction_preview.set("Select a habitat and a compatible species. Choose 1–10 animals.")
            self.introduction_button.configure(state="disabled")
            return
        region_id, habitat_id = self._locations[selected[0]]
        cooldown = self.controller.world.intervention_resources.introduction_cooldown_months
        date = self.controller.world.calendar
        target = (f"{self.registry.get(habitat_id)['name']} · {date.day} {date.month.display_name}, Year {date.year}\n"
                  "Cost 4 IC · recovery 3 months\n")
        try:
            quote = preview_population_introduction(self.controller.world, self.registry, region_id, habitat_id,
                                                    self._introduction_options[self.introduction_species.get()],
                                                    int(self.introduction_amount.get()))
        except (ValueError, TypeError) as error:
            self.introduction_preview.set(target + (f"Charge: {cooldown} monthly completion(s) remaining.\n" if cooldown else "") + str(error))
            self.introduction_button.configure(state="disabled")
            return
        self.introduction_preview.set(target + f"{quote.quantity} healthy arrivals · local population: {quote.local_before} → {quote.local_after}\n"
                                       f"IC after: {quote.resources_after.ic:g}" + ("\nPause before applying." if self.controller.running else ""))
        self.introduction_button.configure(state="disabled" if self.controller.running else "normal")

    def close(self):
        self._pause()
        self.root.destroy()


def launch(project_root: Path | None = None):
    root = tk.Tk()
    try:
        EcoSimApp(root, project_root or Path(__file__).resolve().parents[1])
    except Exception:
        root.destroy()
        raise
    root.mainloop()
