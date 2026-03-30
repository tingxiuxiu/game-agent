import time
import logging
from typing import Dict, Tuple, Optional, Any
from enum import Enum
from .screen_ops import ScreenController


class ShimenTaskType(Enum):
    KILL_MONSTER = 'kill_monster'
    COLLECT_ITEM = 'collect_item'
    DELIVER_ITEM = 'deliver_item'
    TALK_TO_NPC = 'talk_to_npc'
    UNKNOWN = 'unknown'


class ShimenTask:
    def __init__(self, screen_controller: ScreenController, config: Optional[Dict[str, Any]] = None):
        self.screen = screen_controller
        self.logger = logging.getLogger(__name__)
        
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
        
        self.window_handle: Optional[int] = None
        self.current_task: Optional[ShimenTaskType] = None
        self.task_count = 0
        self.max_tasks = 10
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'window_title': '幻唐志',
            'positions': {
                'npc_shifu': (500, 400),
                'accept_task_btn': (800, 600),
                'submit_task_btn': (800, 600),
                'confirm_btn': (700, 550),
                'close_dialog': (950, 100),
            },
            'colors': {
                'npc_highlight': (255, 215, 0),
                'dialog_bg': (240, 230, 200),
                'task_accepted': (0, 255, 0),
            },
            'delays': {
                'click': 0.5,
                'page_load': 2.0,
                'dialog': 1.0,
                'retry': 1.0,
            },
            'max_retries': 3,
        }
    
    def activate_game_window(self) -> bool:
        try:
            hwnd = self.screen.find_window(self.config['window_title'])
            if hwnd:
                self.screen.activate_window(hwnd)
                self.window_handle = hwnd
                self.logger.info(f"已激活游戏窗口: {hwnd}")
                return True
            self.logger.error(f"未找到游戏窗口: {self.config['window_title']}")
            return False
        except Exception as e:
            self.logger.error(f"激活窗口失败: {e}")
            return False
    
    def wait(self, seconds: Optional[float] = None):
        delay = seconds or self.config['delays']['page_load']
        time.sleep(delay)
    
    def click_at_position(self, position_key: str, retries: int = 3) -> bool:
        pos = self.config['positions'].get(position_key)
        if not pos:
            self.logger.error(f"未找到位置配置: {position_key}")
            return False
        
        for attempt in range(retries):
            try:
                self.screen.click_at(pos[0], pos[1])
                self.wait(self.config['delays']['click'])
                self.logger.info(f"点击位置 {position_key}: {pos}")
                return True
            except Exception as e:
                self.logger.warning(f"点击失败 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    self.wait(self.config['delays']['retry'])
        return False
    
    def click_dialog_confirm(self) -> bool:
        return self.click_at_position('confirm_btn')
    
    def close_dialog(self) -> bool:
        return self.click_at_position('close_dialog')
    
    def check_screen_state(self, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        try:
            screenshot = self.screen.screenshot(region=region)
            width, height = screenshot.size
            
            center_color = screenshot.getpixel((width // 2, height // 2))
            
            state = {
                'has_image': True,
                'center_color': center_color,
                'width': width,
                'height': height,
            }
            return state
        except Exception as e:
            self.logger.error(f"检查屏幕状态失败: {e}")
            return {'has_image': False}
    
    def identify_task_type(self) -> ShimenTaskType:
        state = self.check_screen_state()
        return ShimenTaskType.UNKNOWN
    
    def step1_find_and_click_npc(self) -> bool:
        self.logger.info("步骤1: 查找并点击师父NPC")
        return self.click_at_position('npc_shifu')
    
    def step2_accept_task(self) -> bool:
        self.logger.info("步骤2: 接受师门任务")
        self.wait()
        if self.click_at_position('accept_task_btn'):
            self.wait()
            self.current_task = self.identify_task_type()
            self.logger.info(f"识别到任务类型: {self.current_task}")
            return True
        return False
    
    def step3_execute_task(self) -> bool:
        self.logger.info(f"步骤3: 执行任务 - {self.current_task}")
        
        if self.current_task == ShimenTaskType.KILL_MONSTER:
            return self._execute_kill_monster()
        elif self.current_task == ShimenTaskType.COLLECT_ITEM:
            return self._execute_collect_item()
        elif self.current_task == ShimenTaskType.DELIVER_ITEM:
            return self._execute_deliver_item()
        elif self.current_task == ShimenTaskType.TALK_TO_NPC:
            return self._execute_talk_to_npc()
        else:
            self.logger.warning("未知任务类型，使用默认流程")
            self.wait(5.0)
            return True
    
    def _execute_kill_monster(self) -> bool:
        self.logger.info("执行杀怪任务")
        self.wait(3.0)
        return True
    
    def _execute_collect_item(self) -> bool:
        self.logger.info("执行收集物品任务")
        self.wait(3.0)
        return True
    
    def _execute_deliver_item(self) -> bool:
        self.logger.info("执行递送物品任务")
        self.wait(3.0)
        return True
    
    def _execute_talk_to_npc(self) -> bool:
        self.logger.info("执行与NPC对话任务")
        self.wait(3.0)
        return True
    
    def step4_submit_task(self) -> bool:
        self.logger.info("步骤4: 提交任务")
        if not self.click_at_position('npc_shifu'):
            return False
        self.wait()
        if not self.click_at_position('submit_task_btn'):
            return False
        self.wait()
        self.click_dialog_confirm()
        return True
    
    def step5_complete_cycle(self) -> bool:
        self.task_count += 1
        self.logger.info(f"完成第 {self.task_count} 轮任务")
        
        if self.task_count >= self.max_tasks:
            self.logger.info(f"已完成 {self.max_tasks} 轮任务，结束流程")
            return False
        return True
    
    def run_single_cycle(self) -> bool:
        if not self.activate_game_window():
            return False
        
        steps = [
            self.step1_find_and_click_npc,
            self.step2_accept_task,
            self.step3_execute_task,
            self.step4_submit_task,
            self.step5_complete_cycle,
        ]
        
        for i, step in enumerate(steps, 1):
            try:
                if not step():
                    self.logger.error(f"步骤 {i} 失败")
                    return False
            except Exception as e:
                self.logger.error(f"步骤 {i} 执行异常: {e}")
                return False
        
        return True
    
    def run(self, max_tasks: Optional[int] = None) -> Dict[str, Any]:
        if max_tasks:
            self.max_tasks = max_tasks
        
        self.task_count = 0
        self.logger.info(f"开始师门任务，目标: {self.max_tasks} 轮")
        
        success_count = 0
        fail_count = 0
        
        while self.task_count < self.max_tasks:
            try:
                if self.run_single_cycle():
                    success_count += 1
                else:
                    fail_count += 1
                    self.logger.warning(f"当前轮次失败，已失败 {fail_count} 次")
                    
                    if fail_count >= self.config['max_retries']:
                        self.logger.error("连续失败次数过多，终止任务")
                        break
            except Exception as e:
                self.logger.error(f"执行异常: {e}")
                fail_count += 1
                self.wait(self.config['delays']['retry'])
        
        result = {
            'success': success_count > 0,
            'success_count': success_count,
            'fail_count': fail_count,
            'total_tasks': self.task_count,
        }
        
        self.logger.info(f"师门任务结束: {result}")
        return result
