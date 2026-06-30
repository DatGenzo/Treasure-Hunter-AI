"""
game_scene.py — The primary gameplay scene handling map, camera, entities, HUD, AI visualisation, and pause states.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import logging

# pyrefly: ignore [missing-import]
import pygame

from config.settings import GAME_HEIGHT, GAME_WIDTH, TILE_SIZE, WARNING, TEXT_PRIMARY
from config.level_config import LEVEL_MAP
from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine
from entities.item import Item, ItemType
from entities.player import Player
from entities.monster import Monster
from entities.door import Door
from entities.key_item import KeyItem
from entities.puzzle_trigger import PuzzleTrigger
from entities.chest import Chest
from systems.mission_system import MissionSystem, MissionStep
from systems.stats_tracker import StatsTracker, RunStats
from maps.loader import load_level
from scene.base_scene import BaseScene
from ui.hud import HUD
from ui.ai_panel import AIPanel
from ui.widgets import InGameMenu
from utils.vec2 import Vec2
from visualisation import get_overlay
from algorithms import create_algorithm
from maps.fog import FogOfWar
from effects.particle import ParticleSystem
from audio import play_sound, stop_music

logger = logging.getLogger(__name__)


class GameScene(BaseScene):
    """The main gameplay scene handling level layout, camera, and game state routing.

    Args:
        bus:           Shared EventBus.
        state_machine: Shared StateMachine.
        game_surface:  The left side canvas surface.
        panel_surface: The right side control panel surface.
        level_id:      The index of the level currently loaded.
    """

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        game_surface: pygame.Surface,
        panel_surface: pygame.Surface,
        level_id: int,
    ) -> None:
        super().__init__(bus, state_machine, game_surface)
        self._panel_surface = panel_surface
        self._level_id = level_id

        # Load level configuration and construct the tilemap
        self._tilemap = load_level(self._level_id)

        # Spawn Player
        spawn = self._tilemap.spawn_pos
        self._player = Player(spawn.x, spawn.y, self._tilemap, self._bus)

        # Spawn Items (use KeyItem for keys)
        self._items: List[Item] = []
        for col, row, type_str in self._tilemap.item_spawns:
            if type_str == "key":
                self._items.append(KeyItem(col, row, self._tilemap))
            else:
                item_type = ItemType.TREASURE
                if type_str == "potion":
                    item_type = ItemType.HEALTH_POTION
                self._items.append(Item(col, row, item_type, self._tilemap))

        # Spawn Monsters
        self._monsters: List[Monster] = []
        for col, row, type_str in self._tilemap.monster_spawns:
            patrol = [(col, row), (col, max(0, row - 3)), (col, row)]
            self._monsters.append(Monster(col, row, self._tilemap, patrol_path=patrol))

        # Spawn Doors dynamically
        self._doors: List[Door] = []
        for door_info in getattr(self._tilemap, "doors_data", []):
            color = door_info.get("color")
            color_val = tuple(color) if color is not None else None
            self._doors.append(Door(
                col=door_info["col"],
                row=door_info["row"],
                tilemap=self._tilemap,
                bus=self._bus,
                door_id=door_info["id"],
                key_required=door_info["key_required"],
                puzzle_id=door_info["puzzle_id"],
                color=color_val
            ))

        # Spawn Puzzle Triggers dynamically
        self._puzzle_triggers: List[PuzzleTrigger] = []
        for p_info in getattr(self._tilemap, "puzzle_triggers_data", []):
            color = p_info.get("color")
            color_val = tuple(color) if color is not None else None
            self._puzzle_triggers.append(PuzzleTrigger(
                col=p_info["col"],
                row=p_info["row"],
                puzzle_id=p_info["puzzle_id"],
                tilemap=self._tilemap,
                bus=self._bus,
                color=color_val
            ))

        # Spawn Chests dynamically
        self._chests: List[Chest] = []
        for c_info in getattr(self._tilemap, "chest_data", []):
            self._chests.append(Chest(
                col=c_info["col"],
                row=c_info["row"],
                tilemap=self._tilemap,
                bus=self._bus,
                treasure_value=c_info.get("value", 50),
            ))

        # Stats Tracker
        self._stats_tracker = StatsTracker()

        # Configure level objectives in MissionSystem
        self._mission_system = MissionSystem()
        if self._tilemap.missions_data:
            self._mission_system.load_from_json_data(self._tilemap.missions_data)
        else:
            m_steps = []
            if self._level_id == 1:
                m_steps = [MissionStep("reach_exit", "Reach the Exit Portal", "🚪")]
            elif self._level_id == 2:
                m_steps = [
                    MissionStep("collect_key", "Collect the Gate Key", "🔑"),
                    MissionStep("unlock_door", "Unlock the Exit Gate", "🚪"),
                    MissionStep("reach_exit", "Reach the Exit Portal", "🚪")
                ]
            elif self._level_id == 3:
                m_steps = [MissionStep("reach_exit", "Reach the Exit Portal", "🚪")]
            elif self._level_id == 4:
                m_steps = [
                    MissionStep("solve_puzzle", "Solve the Gem Puzzle", "🧩"),
                    MissionStep("reach_exit", "Reach the Exit Portal", "🚪")
                ]
            elif self._level_id == 5:
                m_steps = [
                    MissionStep("collect_key", "Collect the Gate Key", "🔑"),
                    MissionStep("unlock_door", "Unlock the Exit Gate", "🚪"),
                    MissionStep("reach_exit", "Reach the Exit Portal", "🚪")
                ]
            elif self._level_id == 6:
                m_steps = [
                    MissionStep("solve_puzzle", "Solve the Chamber Puzzle", "🧩"),
                    MissionStep("collect_key", "Collect the Exit Key", "🔑"),
                    MissionStep("unlock_door", "Unlock the Exit Gate", "🚪"),
                    MissionStep("reach_exit", "Reach the Exit Portal", "🚪")
                ]
            else:
                m_steps = [MissionStep("reach_exit", "Reach the Exit Portal", "🚪")]

            for step in m_steps:
                self._mission_system.add_step(step)

        # HUD instance
        self._hud = HUD()

        # Fog of War
        self._fog = FogOfWar(self._tilemap.width, self._tilemap.height) if LEVEL_MAP[self._level_id].fog_of_war else None

        # Particle System
        self._particles = ParticleSystem()

        # Stats tracking
        self._run_time = 0.0
        self._path_cost = 0.0
        self._nodes_expanded = 0
        self._steps_taken = 0
        self._last_player_grid = spawn.to_tuple()
        self._victory_timer = 0.0
        self._victory_triggered = False

        # AI panel
        self._ai_panel = AIPanel(self._bus, self._sm, LEVEL_MAP[self._level_id].allowed_algorithms, self._mission_system)

        # AI visualisation state
        self._active_algorithm_key: str = ""
        self._last_vis_data: Optional[Dict[str, Any]] = None
        self._current_subgoal: Optional[Tuple[int, int]] = None
        self._current_subgoal_desc: str = ""
        from systems.goal_planner import GoalPlanner
        self._goal_planner = GoalPlanner(self._mission_system, self._tilemap, self._bus)

        # Initialize camera tracking offset
        self._camera_offset = Vec2(0, 0)
        self._font = pygame.font.SysFont("consolas", 18)
        self._title_font = pygame.font.SysFont("consolas", 28, bold=True)
        self._ingame_menu = InGameMenu(self._bus, self._sm)

        logger.info(
            "GameScene loaded. Spawned Player at (%d, %d), %d items.",
            spawn.x,
            spawn.y,
            len(self._items),
        )

    def on_enter(self) -> None:
        """Called when this scene becomes the active scene."""
        logger.info("Entering GameScene for Level %d", self._level_id)
        stop_music()
        self._bus.subscribe(Events.AI_START, self._on_ai_start)
        self._bus.subscribe(Events.AI_STARTED, self._on_ai_started)
        self._bus.subscribe(Events.AI_STOPPED, self._on_ai_stopped)
        self._bus.subscribe(Events.AI_STEP_COMPLETED, self._on_ai_step)
        self._bus.subscribe("puzzle_triggered", self._on_puzzle_triggered)
        self._bus.subscribe(Events.GAME_OVER, self._on_game_over_event)
        self._bus.subscribe("ai_subgoal_reached_check", self._on_ai_subgoal_reached_check)
        self._bus.subscribe("ai_subgoal_changed", self._on_ai_subgoal_changed)
        self._bus.subscribe("chest_opened", self._on_chest_opened)

    def on_exit(self) -> None:
        """Clean up when exiting this scene."""
        logger.info("Exiting GameScene for Level %d", self._level_id)
        self._ai_panel.cleanup()
        self._bus.unsubscribe(Events.AI_START, self._on_ai_start)
        self._bus.unsubscribe(Events.AI_STARTED, self._on_ai_started)
        self._bus.unsubscribe(Events.AI_STOPPED, self._on_ai_stopped)
        self._bus.unsubscribe(Events.AI_STEP_COMPLETED, self._on_ai_step)
        self._bus.unsubscribe("puzzle_triggered", self._on_puzzle_triggered)
        self._bus.unsubscribe(Events.GAME_OVER, self._on_game_over_event)
        self._bus.unsubscribe("ai_subgoal_reached_check", self._on_ai_subgoal_reached_check)
        self._bus.unsubscribe("ai_subgoal_changed", self._on_ai_subgoal_changed)
        self._bus.unsubscribe("chest_opened", self._on_chest_opened)

    def _on_puzzle_triggered(self, puzzle_id: str = "", **kwargs: Any) -> None:
        p_id = puzzle_id or kwargs.get("puzzle_id", "")
        logger.info("GameScene: Triggering puzzle %s", p_id)
        auto_solve = (self._active_algorithm_key != "")
        from scene.puzzle_scene import PuzzleScene
        puzzle = PuzzleScene(
            bus=self._bus,
            state_machine=self._sm,
            game_surface=self._surface,
            panel_surface=self._panel_surface,
            puzzle_id=p_id,
            auto_solve=auto_solve
        )
        self._bus.publish("push_scene", scene=puzzle)

    def _on_chest_opened(self, col: int = 0, row: int = 0, value: int = 0, **kwargs: Any) -> None:
        """Log gold earned from a chest."""
        gold = value or kwargs.get("value", 0)
        logger.info("Chest opened at (%d, %d) — +%d gold (total: %d)", col, row, gold, self._player.inventory.gold)

    def _on_game_over_event(self) -> None:
        logger.info("GameScene: Player died. Saving run statistics.")
        from entities.item import ItemType
        total_treasures = sum(1 for item in self._items if item.item_type == ItemType.TREASURE)
        required_steps = [s for s in self._mission_system.steps if not s.is_optional]
        completed_steps = sum(1 for s in required_steps if s.completed)
        completion_pct = (completed_steps / len(required_steps) * 100.0) if required_steps else 0.0

        run_stats = RunStats(
            is_ai=bool(self._active_algorithm_key),
            algorithm_key=self._active_algorithm_key,
            time_elapsed=self._run_time,
            path_cost=self._path_cost,
            nodes_expanded=self._nodes_expanded,
            treasures_collected=self._player.inventory.treasures,
            deaths=1,
            combat_wins=0,
            steps_taken=self._steps_taken,
            memory_peak=0,
            treasures_total=total_treasures,
            completion_pct=completion_pct,
            hp_remaining=0,
            star_rating=1
        )
        self._stats_tracker.save_run(self._level_id, run_stats)

    def _on_ai_start(self, algorithm_key: str, speed: float) -> None:
        """Initialize the AI algorithm and tell the runner to set it."""
        logger.info("GameScene: Instantiating algorithm '%s' at speed %.1f", algorithm_key, speed)
        # 1. Instantiate the algorithm using factory
        algorithm = create_algorithm(algorithm_key)
        self._current_algorithm = algorithm
        # 2. Call initialization with first subgoal from goal planner
        snap = self._player.get_game_state_snapshot(self)
        first_target = self._goal_planner.plan_next_goal(snap)
        algorithm.initialise(
            self._player.grid_pos,
            first_target,
            self._tilemap,
            snap
        )
        # 4. Transition StateMachine
        self._sm.transition(GameState.AI_RUNNING)
        # 5. Notify the rest of the game (resets panel stats, must happen before sending target)
        self._bus.publish(Events.AI_STARTED, algorithm_key=algorithm_key)
        # 6. Publish to AI Runner to set it up and publish initial subgoal
        self._bus.publish("set_ai_algorithm", algorithm=algorithm, speed=speed)
        self._bus.publish("ai_subgoal_changed", target=first_target, description=self._goal_planner.get_goal_description())

    def _on_ai_subgoal_reached_check(self) -> None:
        if self._sm.state != GameState.AI_RUNNING or not hasattr(self, "_current_algorithm") or self._current_algorithm is None:
            return
        
        snap = self._player.get_game_state_snapshot(self)
        all_completed = self._goal_planner.on_subgoal_reached(snap)
        
        if all_completed:
            logger.info("All objectives completed! Stopping AI.")
            self._bus.publish("ai_stop")
        else:
            next_target = self._goal_planner.plan_next_goal(snap)
            self._bus.publish("ai_subgoal_changed", target=next_target, description=self._goal_planner.get_goal_description())
            logger.info("AI Subgoal reached. Planning next: %s to %s", self._goal_planner.get_goal_description(), next_target)
            
            # Re-initialize the existing algorithm object in-place!
            self._current_algorithm.initialise(
                self._player.grid_pos,
                next_target,
                self._tilemap,
                snap
            )

    def _on_ai_subgoal_changed(self, target: Tuple[int, int], description: str) -> None:
        self._current_subgoal = target
        self._current_subgoal_desc = description

    def _on_ai_started(self, algorithm_key: str = "", **kwargs: Any) -> None:
        """Handler for AI process startup."""
        self._active_algorithm_key = algorithm_key or kwargs.get("algorithm_key", "")
        self._last_vis_data = None
        self._ai_stop_logged = False
        logger.info("GameScene: AI started with algorithm '%s'", self._active_algorithm_key)

    def _on_ai_stopped(self) -> None:
        """Handler for AI process shutdown."""
        # Keep active_algorithm_key and last_vis_data so the path overlay remains visible!
        if not getattr(self, '_ai_stop_logged', False):
            logger.info("GameScene: AI stopped.")
            self._ai_stop_logged = True

    def _on_ai_step(self, step: Any) -> None:
        """Handler for single search/execution steps from the runner."""
        # Note: step is a StepResult dataclass instance
        self._last_vis_data = step.vis_data
        
        # Accumulate search space sizes
        if step.vis_data:
            visited = step.vis_data.get("visited") or step.vis_data.get("closed_set") or step.vis_data.get("beams") or []
            self._nodes_expanded = len(visited)
        
        # If the step yields a movement command, drive player character
        if step.action and step.action.startswith("move_"):
            dx, dy = 0, 0
            if step.action == "move_n":
                dy = -1
            elif step.action == "move_s":
                dy = 1
            elif step.action == "move_w":
                dx = -1
            elif step.action == "move_e":
                dx = 1

            if dx != 0 or dy != 0:
                px, py = self._player.grid_pos
                target_pos = (px + dx, py + dy)
                for door in self._doors:
                    if door.locked and door.grid_pos == target_pos:
                        if door.unlock(self._player):
                            play_sound("door_open")
                        break

            self._player.move_in_direction(step.action, self._tilemap)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process keyboard, mouse, and game flow events."""
        # 1. Forward to in-game menu first
        if self._ingame_menu.handle_event(event):
            return

        # 2. Forward to AI Panel (offset by game width)
        self._ai_panel.handle_event(event, offset_x=GAME_WIDTH)

        # 3. Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if self._sm.state == GameState.PLAYING:
                if event.key == pygame.K_p:
                    # Push Puzzle minigame!
                    from scene.puzzle_scene import PuzzleScene
                    puzzle = PuzzleScene(
                        bus=self._bus,
                        state_machine=self._sm,
                        game_surface=self._surface,
                        panel_surface=self._panel_surface,
                    )
                    self._bus.publish("push_scene", scene=puzzle)
                elif event.key == pygame.K_f:
                    # Try to unlock adjacent door
                    px, py = self._player.grid_pos
                    for door in self._doors:
                        if door.locked:
                            dx, dy = door.grid_pos
                            if abs(px - dx) + abs(py - dy) <= 1:
                                if door.unlock(self._player):
                                    play_sound("door_open")
                                break
                    # Also try to open adjacent / same-tile chests
                    for chest in self._chests:
                        if chest.state == "CLOSED" and chest.active:
                            cx, cy = chest.grid_pos
                            if abs(px - cx) + abs(py - cy) <= 1:
                                if chest.try_open(self._player):
                                    play_sound("collect_item")
                                break

    def update(self, dt: float) -> None:
        """Update game entities, camera tracking, and AI budget."""
        # Freeze logic updates when paused
        if self._sm.state == GameState.PAUSED:
            return

        # 1. Update player input (only if player is in control / GameState.PLAYING)
        if self._sm.state == GameState.PLAYING:
            keys = pygame.key.get_pressed()
            self._player.handle_input(keys, self._tilemap, dt)

        # 2. Update player movement logic
        self._player.update(dt)

        # Update Mission System
        snap = self._player.get_game_state_snapshot(self)
        self._mission_system.update(snap)

        # Check puzzle triggers
        if self._sm.state in {GameState.PLAYING, GameState.AI_RUNNING}:
            for trigger in self._puzzle_triggers:
                if trigger.check_trigger(self._player.grid_pos):
                    if self._sm.state == GameState.AI_RUNNING:
                        self._bus.publish("ai_pause")
                    break

        # Update Fog of War
        if self._fog is not None:
            self._fog.reveal(self._player.grid_pos[0], self._player.grid_pos[1], radius=4)

        # Update Particles
        self._particles.update(dt)

        # 3. Update active monsters and check combat trigger
        if self._sm.state in {GameState.PLAYING, GameState.AI_RUNNING}:
            # Increment elapsed run time
            if not self._victory_triggered:
                self._run_time += dt

            # Track player path cost when entering new grid tile
            curr_grid = self._player.grid_pos
            if curr_grid != self._last_player_grid:
                self._path_cost += self._tilemap.move_cost(curr_grid[0], curr_grid[1])
                self._steps_taken += 1
                self._last_player_grid = curr_grid

                # Trap / Lava collision detection — damage player on tile entry
                from maps.tile import TileType
                tile = self._tilemap.get_tile(curr_grid[0], curr_grid[1])
                if tile.tile_type == TileType.TRAP:
                    alive = self._player.take_damage(10)
                    self._particles.spawn_collect(
                        self._player.world_pos.x, self._player.world_pos.y, (200, 40, 40)
                    )
                    play_sound("combat_hit")
                    logger.info("Player stepped on TRAP at %s, took 10 damage. HP=%d", curr_grid, self._player.hp)
                    if not alive:
                        return
                elif tile.tile_type == TileType.LAVA:
                    alive = self._player.take_damage(20)
                    self._particles.spawn_collect(
                        self._player.world_pos.x, self._player.world_pos.y, (255, 120, 30)
                    )
                    play_sound("combat_hit")
                    logger.info("Player stepped on LAVA at %s, took 20 damage. HP=%d", curr_grid, self._player.hp)
                    if not alive:
                        return

            for monster in self._monsters:
                if monster.active:
                    monster.update_ai(dt, self._player.grid_pos, self._tilemap)
                    
                    # Combat check
                    if monster.state == "ATTACK":
                        logger.info("Combat trigger activated!")
                        was_ai_running = (self._sm.state == GameState.AI_RUNNING)
                        if was_ai_running:
                            self._bus.publish("ai_pause")
                        else:
                            self._bus.publish("ai_stop")
                        play_sound("combat_hit")
                        
                        from scene.combat_scene import CombatScene
                        combat = CombatScene(
                            bus=self._bus,
                            state_machine=self._sm,
                            game_surface=self._surface,
                            panel_surface=self._panel_surface,
                            player=self._player,
                            monster=monster,
                            auto_resume_ai=was_ai_running,
                        )
                        self._bus.publish("push_scene", scene=combat)
                        self._sm.transition(GameState.COMBAT)
                        break

        # 4. Update item animation and check collection
        for item in self._items:
            if item.active and not item.collected:
                item.update(dt)
                # Check collision on grid coordinates
                if item.grid_pos == self._player.grid_pos:
                    self._player.collect_item(item)
                    self._particles.spawn_collect(item.world_pos.x, item.world_pos.y, item.color)
                    play_sound("collect_item")

        # 4b. Update chests and auto-open when AI steps on same tile
        for chest in self._chests:
            chest.update(dt)
            if chest.state == "CLOSED" and chest.active:
                if self._sm.state == GameState.AI_RUNNING:
                    # AI auto-collects chest when standing on same tile
                    if chest.grid_pos == self._player.grid_pos:
                        chest.try_open(self._player)
                        play_sound("collect_item")

        # 4. Check level exit condition
        if self._player.grid_pos == (self._tilemap.exit_pos.x, self._tilemap.exit_pos.y) and not self._victory_triggered:
            logger.info("Player reached the exit! Beginning level completion transition.")
            self._victory_triggered = True
            self._victory_timer = 1.5
            self._particles.spawn_level_complete(self._player.world_pos.x, self._player.world_pos.y)
            play_sound("level_complete")

        # Handle Victory transition timer delay
        if self._victory_triggered:
            self._victory_timer -= dt
            if self._victory_timer <= 0.0:
                # Calculate total treasures and collected treasures
                from entities.item import ItemType
                total_treasures = sum(1 for item in self._items if item.item_type == ItemType.TREASURE)
                collected_treasures = self._player.inventory.treasures
                treasures_pct = (collected_treasures / total_treasures * 100.0) if total_treasures > 0 else 100.0
                hp_pct = (self._player.hp / self._player.max_hp * 100.0) if self._player.max_hp > 0 else 0.0

                stats = {
                    "time": self._run_time,
                    "cost": self._path_cost,
                    "nodes": self._nodes_expanded,
                    "is_ai": bool(self._active_algorithm_key),
                    "steps_taken": self._steps_taken,
                    "treasures_pct": treasures_pct,
                    "hp_pct": hp_pct
                }
                # Compute star rating
                if treasures_pct >= 99.0 and hp_pct >= 50.0 and self._mission_system.all_required_completed():
                    star_rating = 3
                elif treasures_pct >= 50.0 or hp_pct >= 30.0:
                    star_rating = 2
                else:
                    star_rating = 1

                # Completion percentage based on mission steps
                required_steps = [s for s in self._mission_system.steps if not s.is_optional]
                completed_steps = sum(1 for s in required_steps if s.completed)
                completion_pct = (completed_steps / len(required_steps) * 100.0) if required_steps else 100.0

                # Save statistics in StatsTracker
                run_stats = RunStats(
                    is_ai=bool(self._active_algorithm_key),
                    algorithm_key=self._active_algorithm_key,
                    time_elapsed=self._run_time,
                    path_cost=self._path_cost,
                    nodes_expanded=self._nodes_expanded,
                    treasures_collected=self._player.inventory.treasures,
                    deaths=0,
                    combat_wins=0,
                    steps_taken=self._steps_taken,
                    memory_peak=0,
                    treasures_total=total_treasures,
                    completion_pct=completion_pct,
                    hp_remaining=self._player.hp,
                    star_rating=star_rating
                )
                self._stats_tracker.save_run(self._level_id, run_stats)
                self._bus.publish(Events.LEVEL_COMPLETE, level_id=self._level_id, stats=stats)
                self._sm.transition(GameState.LEVEL_COMPLETE)

        # 5. Camera follow player with clamping
        map_width_px = self._tilemap.width * TILE_SIZE
        map_height_px = self._tilemap.height * TILE_SIZE

        VIEWPORT_Y = 50
        VIEWPORT_HEIGHT = GAME_HEIGHT - 100

        cx = self._player.world_pos.x - GAME_WIDTH // 2
        cy = self._player.world_pos.y - VIEWPORT_HEIGHT // 2 - VIEWPORT_Y

        # Clamp camera to bounds of the map (protect against smaller maps than screens)
        cx = max(0, min(cx, max(0, map_width_px - GAME_WIDTH)))
        cy = max(-VIEWPORT_Y, min(cy, max(-VIEWPORT_Y, map_height_px - VIEWPORT_HEIGHT - VIEWPORT_Y)))
        self._camera_offset = Vec2(cx, cy)

    def render(self, surface: pygame.Surface) -> None:
        """Render the map and all active game objects onto the game surface."""
        surface.fill((10, 10, 15))  # Base background color

        # Layer 1: Tile Map
        self._tilemap.render(surface, self._camera_offset)

        # Layer 2: Exit tile highlight
        exit_tile_world = self._tilemap.grid_to_world(
            self._tilemap.exit_pos.x, self._tilemap.exit_pos.y
        )
        exit_rect = pygame.Rect(
            exit_tile_world.x - TILE_SIZE // 2 - self._camera_offset.x,
            exit_tile_world.y - TILE_SIZE // 2 - self._camera_offset.y,
            TILE_SIZE,
            TILE_SIZE,
        )
        pygame.draw.rect(surface, (100, 255, 120), exit_rect, 3, border_radius=4)

        # Layer 2.5: Doors
        for door in self._doors:
            door.render(surface, self._camera_offset)

        # Layer 2.6: Puzzle Triggers
        for trigger in self._puzzle_triggers:
            trigger.render(surface, self._camera_offset)

        # Layer 3: AI Search overlays (drawn under items and player)
        if self._active_algorithm_key and self._last_vis_data:
            overlay = get_overlay(self._active_algorithm_key)
            overlay.render(surface, self._last_vis_data, self._camera_offset, self._tilemap)

        # Layer 4: Items & Monsters
        for item in self._items:
            item.render(surface, self._camera_offset)

        for chest in self._chests:
            chest.render(surface, self._camera_offset)

        for monster in self._monsters:
            if monster.active:
                monster.render(surface, self._camera_offset)

        # Layer 5: Player character
        self._player.render(surface, self._camera_offset)

        # Layer 6: Particles overlay
        self._particles.render(surface, self._camera_offset)

        # Layer 7: Fog of War overlay
        if self._fog is not None:
            self._fog.render(surface, self._camera_offset)

        # Layer 6: HUDOverlay
        self._hud.render(surface, self._player, self._level_id, self._active_algorithm_key.upper(), self._mission_system)

        # Layer 7: Draw in-game menu
        self._ingame_menu.render(surface)

    def render_panel(self, panel: pygame.Surface) -> None:
        """Render the AI stats, controls, and legends panel on the right side."""
        self._ai_panel.render(panel)
