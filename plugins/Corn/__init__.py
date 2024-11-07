from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app import schemas
from app.core.config import settings
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.log import logger

class CronExpressionGenerator(_PluginBase):
    # 插件基础信息
    plugin_name = "Cron 表达式生成器"
    plugin_desc = "自动生成 Cron 表达式并定期触发任务。"
    plugin_icon = "cron_icon.png"
    plugin_version = "1.0"
    plugin_author = "Your Name"
    author_url = "https://github.com/yourusername"
    plugin_config_prefix = "cron_gen_"
    plugin_order = 10
    auth_level = 1

    # 私有属性
    _enabled = False
    _cron = None
    _onlyonce = False
    _notify = False
    _scheduler: Optional[BackgroundScheduler] = None

    def init_plugin(self, config: dict = None):
        """
        插件初始化方法
        """
        # 停止现有任务
        self.stop_service()

        if config:
            self._enabled = config.get("enabled", False)
            self._cron = config.get("cron", "* * * * *")
            self._notify = config.get("notify", False)
            self._onlyonce = config.get("onlyonce", False)

            # 启动 Cron 表达式生成任务
            if self._enabled and self._cron:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                logger.info(f"Cron 表达式生成器插件已启用，启动定时任务")
                self._scheduler.add_job(func=self.__generate_cron_expression, trigger='cron', 
                                        **self._parse_cron(self._cron), name="生成 Cron 表达式任务")
                if self._scheduler.get_jobs():
                    self._scheduler.start()

    def __generate_cron_expression(self):
        """
        生成 Cron 表达式，并执行相应的任务
        """
        logger.info(f"生成 Cron 表达式任务开始：{self._cron}")
        # 在这里你可以添加 Cron 表达式生成的逻辑，或者触发一个实际的任务
        if self._notify:
            self.post_message(
                mtype=NotificationType.SiteMessage,
                title="【Cron 表达式生成完成】",
                text=f"Cron 表达式已生成：{self._cron}"
            )

    def _parse_cron(self, cron_str: str) -> dict:
        """
        解析 Cron 表达式字符串，并转为 APScheduler 所需的字典格式
        """
        cron_parts = cron_str.split(" ")
        if len(cron_parts) != 5:
            raise ValueError("Cron 表达式必须是 5 位")
        
        return {
            'minute': cron_parts[0],
            'hour': cron_parts[1],
            'day': cron_parts[2],
            'month': cron_parts[3],
            'day_of_week': cron_parts[4]
        }

    def get_state(self) -> bool:
        """
        获取插件的启用状态
        """
        return self._enabled

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件的 API 接口
        """
        return [{
            "path": "/generate-cron",
            "endpoint": self.api_generate_cron,
            "methods": ["GET"],
            "summary": "手动触发 Cron 表达式生成",
            "description": "手动调用 Cron 表达式生成方法，触发生成任务"
        }]

    def api_generate_cron(self, apikey: str):
        """
        API 接口，手动触发 Cron 表达式生成任务
        """
        if apikey != settings.API_TOKEN:
            return schemas.Response(success=False, message="API 密钥错误")
        self.__generate_cron_expression()
        return schemas.Response(success=True, message="Cron 表达式生成任务已触发")

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取插件配置页面表单
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'notify',
                                            'label': '启用通知',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 12},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cron',
                                            'label': 'Cron 表达式'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "cron": "* * * * *",
            "notify": False,
            "onlyonce": False
        }

    def stop_service(self):
        """
        停止插件定时任务服务
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("停止 Cron 表达式生成插件失败：%s" % str(e))
