from tests.fakes import FakeClock
from trivia.domain.timer import QuestionTimer


def started_timer(seconds=20):
    clock = FakeClock()
    timer = QuestionTimer(seconds, clock)
    timer.start()
    return timer, clock


def test_counts_down_with_the_clock():
    timer, clock = started_timer()
    clock.advance(5.5)
    assert timer.remaining() == 14.5
    assert timer.seconds_left() == 15  # rounded up, like the countdown a player sees


def test_expires_and_never_goes_negative():
    timer, clock = started_timer()
    clock.advance(25)
    assert timer.expired
    assert timer.remaining() == 0
    assert timer.seconds_left() == 0


def test_pause_freezes_the_countdown_until_resumed():
    timer, clock = started_timer()
    clock.advance(4)
    assert timer.pause() is True
    clock.advance(100)
    assert timer.paused
    assert timer.remaining() == 16
    assert not timer.expired

    assert timer.resume() is True
    clock.advance(6)
    assert timer.remaining() == 10


def test_pause_and_resume_report_when_they_do_nothing():
    timer, _ = started_timer()
    assert timer.resume() is False
    assert timer.pause() is True
    assert timer.pause() is False


def test_unstarted_timer_reports_its_full_duration():
    timer = QuestionTimer(20, FakeClock())
    assert timer.remaining() == 20
