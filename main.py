import Photobot
import logging

main_logger = logging.getLogger(__name__)
main_logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    main_logger.info("Main started")
    bot = Photobot.Photobot()
    bot.run()


