"""Optional human listening, separate from the timestamp-based neural input."""
from pathlib import Path
from PySide6 import QtCore,QtMultimedia

class AudioMonitor:
    def __init__(self,parent):
        self.output=QtMultimedia.QAudioOutput(parent); self.output.setVolume(.5)
        self.player=QtMultimedia.QMediaPlayer(parent); self.player.setAudioOutput(self.output)
        self.enabled=False; self.source=None; self.speed=1.
    def update(self,packet):
        path=Path(packet['name'])
        source=str(path) if path.is_file() else None
        if source!=self.source:
            self.source=source
            self.player.setSource(QtCore.QUrl.fromLocalFile(source) if source else QtCore.QUrl())
        if not self.enabled or source is None or not packet['playing']:
            self.player.pause(); return
        self.player.setPlaybackRate(self.speed)
        target=round(packet['index']/packet['fps']*1000)
        if abs(self.player.position()-target)>150: self.player.setPosition(target)
        if self.player.playbackState()!=QtMultimedia.QMediaPlayer.PlaybackState.PlayingState: self.player.play()
    def close(self): self.player.stop()
