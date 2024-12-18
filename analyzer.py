"""
This module defines an Analyzer class using multiprocessing to analyze network packets 
from a task queue, check for rule-based intrusions, and log findings to a file.
"""

from multiprocessing import Process, Event, Queue
from scapy.all import Ether
from signature import Signature
from rules import load_rules
from typing import Optional, Any, List

class Analyzer(Process):
    """
    A class used to represent a Network Packet Analyzer.
    
    This class inherits from multiprocessing.Process and analyzes network packets 
    from a task queue, checking for rule-based intrusions and logging findings to a file.
    
    Attributes
    ----------
    task_queue : multiprocessing.Queue
        The queue to get packets from.
    log_file : Any
        The file to write log messages to.
    rule_path : str
        The path to the rule file.
    show_non_intrusive : bool
        Whether to show non-intrusive packets.
    rules : List[Signature]
        The loaded rules for packet analysis.
    
    Methods
    -------
    is_dead() -> bool:
        Checks if the analyzer should stop running.
    is_intrusion(packet: Ether, index: int) -> bool:
        Checks if a packet matches any of the loaded rules.
    run() -> None:
        Starts the packet analysis process.
    join(timeout: Optional[int] = None) -> None:
        Stops the analyzer and waits for the process to terminate.
    """

    def __init__(self, task_queue: Queue, log_file: Any, rule_path: str, show_non_intrusive: bool):
        super().__init__()
        self.daemon = True
        self.stop_event = Event()
        self.task_queue = task_queue
        self.log_file = log_file
        self.rule_path = rule_path
        self.show_non_intrusive = show_non_intrusive
        try:
            self.rules = load_rules(self.rule_path)
            print('[*] Parsed rules successfully.')
        except ValueError as err:
            exit(f"[@] Error loading rules: {err}")

    def is_dead(self) -> bool:
        return self.stop_event.is_set()

    def is_intrusion(self, packet: Ether, index: int) -> bool:
        summary = packet.summary()
        try:
            packet_signature = Signature(packet)
        except ValueError as err:
            print(f"[@] Error creating signature: {err} - Packet summary: {summary}")
            return False

        for rule in self.rules:
            if packet_signature == rule:
                msg = f"{rule.__repr__()} ~> {summary}"
                print(f"[!!] Intrusion detected: {msg}")
                self.log_file.write(msg + '\n')
                self.log_file.flush()
                return True

        if self.show_non_intrusive:
            print(f"[=] Non-intrusive packet: {summary}")

        return False

    def run(self) -> None:
        index = 1
        while not self.is_dead():
            packet_data = self.task_queue.get()
            if packet_data is None:
                continue
            packet = Ether(packet_data)
            self.is_intrusion(packet, index)
            index += 1

    def join(self, timeout: Optional[int] = None) -> None:
        self.stop_event.set()
        super().join(timeout)
