import os
import sys
import time

from generator.gpt2.gpt2_generator import *
from story.story_manager import *
from story.utils import *
from func_timeout import func_timeout, FunctionTimedOut

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def splash():
    print("0) New Game\n1) Load Game\n")
    choice = get_num_options(2)

    if choice == 1:
        return "load"
    else:
        return "new"


def select_game():
    with open(YAML_FILE, "r") as stream:
        data = yaml.safe_load(stream)

    print("Pick a setting.")
    settings = data["settings"].keys()
    for i, setting in enumerate(settings):
        print_str = str(i) + ") " + setting
        if setting == "fantasy":
            print_str += " (recommended)"

        console_print(print_str)
    console_print(str(len(settings)) + ") custom")
    choice = get_num_options(len(settings) + 1)

    if choice == len(settings):

        context = ""
        console_print(
            "\nEnter a prompt that describes who you are and the first couple sentences of where you start "
            "out ex:\n 'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been "
            + "terrorizing the kingdom. You enter the forest searching for the dragon and see' "
        )
        prompt = input("Starting Prompt: ")
        return context, prompt

    setting_key = list(settings)[choice]

    print("\nPick a character")
    characters = data["settings"][setting_key]["characters"]
    for i, character in enumerate(characters):
        console_print(str(i) + ") " + character)
    character_key = list(characters)[get_num_options(len(characters))]

    name = input("\nWhat is your name? ")
    setting_description = data["settings"][setting_key]["description"]
    character = data["settings"][setting_key]["characters"][character_key]

    context = (
        "You are "
        + name
        + ", a "
        + character_key
        + " "
        + setting_description
        + "You have a "
        + character["item1"]
        + " and a "
        + character["item2"]
        + ". "
    )
    prompt_num = np.random.randint(0, len(character["prompts"]))
    prompt = character["prompts"][prompt_num]

    return context, prompt


def instructions():
    text = "\nAI Dungeon 2 Instructions:"
    text += '\n Enter actions starting with a verb ex. "go to the tavern" or "attack the orc." (without quotes)'
    text += '\n To speak enter \'say "(thing you want to say)"\' or just "(thing you want to say)" '
    text += '\n To switch to another character type "setchar Character Name" (without quotes). You will need to write in third person '
    text += '\n To control the story directly, type an exclamation mark before a command (example: "!A sword falls from the sky") '
    text += "\n\nThe following commands can be entered for any action: "
    text += '\n  "revert"   Reverts the last action allowing you to pick a different action.'
    text += '\n  "quit"     Quits the game and saves'
    text += '\n  "restart"  Starts a new game and saves your current one'
    text += '\n  "save"     Makes a new save of your game and gives you the save ID'
    text += '\n  "load"     Asks for a save ID and loads the game if the ID is valid'
    text += '\n  "print"    Prints a transcript of your adventure (without extra newline formatting)'
    text += '\n  "help"     Prints these instructions again'
    text += '\n  "censor off/on" to turn censoring off or on.'
    text += '\n  "settemp" to modify the algorithm temperature value (advanced).'
    text += '\n  "setmem" to modify the algorithm memory value aka top_k (advanced).'
    return text


def play_aidungeon_2():

    console_print(
        "AI Dungeon 2 will save and use your actions and game to continually improve AI Dungeon."
        + " If you would like to disable this enter 'nosaving' for any action. This will also turn off the "
        + "ability to save games."
    )

    upload_story = True
    
    # "temperature" dictates randomness. A low temperature means that the AI is
    #  more likely to go with the word that best fits the context, a high
    #  temperature makes the AI more random and it may chose surprising less fitting words
    # original 0.4
    temp = 0.4
 
    # lower top_k is a hard limit of "how many fitting words should I consider",
    #  i.e. lowering this value also limits the AI in creativity
    # original 40
    top_k = 40
    
    # Get user censorship option at startup, allowing NSFW content in the custom prompt:
    censorship = True
 
    console_print("\nBefore we start, would you like to change any advanced settings? (most users should skip this)\n")
    choice = input("1) Change defaults\n-) Press enter to skip\n>")
 
    if choice == "1":
        console_print("\nDefault temperature (lower = slower less random plot): " + str(temp) + "\n" + 
                      "Default memory (aka \"top_k\", lower = more stability less creative): " + 
                      str(top_k) + "\n" + "Default censorship: " + str(censorship) + "\n")
        userinput = input("New temperature (try 0.07-0.4, leave blank for default): ")
        if userinput:
            temp = float(userinput)
        userinput = input("New memory/top_k (try 10-40, leave blank for default): ")
        if userinput:
            top_k = int(userinput)
        censorship = not bool(input("Disable censorship? (leave blank for no): "))
        console_print("\nLaunching with new values... Temperature: " + str(temp) + ", " + 
                      "Memory: " + str(top_k) + ", " + "Censorship: " + str(censorship) + "\n")

    print("\nInitializing AI Dungeon! (This might take a few minutes)\n")
    generator = GPT2Generator()
    story_manager = UnconstrainedStoryManager(generator)
    inference_timeout = 30
    def act(action):
        return func_timeout(inference_timeout, story_manager.act, (action,))
    def notify_hanged():
        console_print(f"That input caused the model to hang (timeout is {inference_timeout}, use infto ## command to change)")
    print("\n")

    with open("opening.txt", "r", encoding="utf-8") as file:
        starter = file.read()
    print(starter)

    while True:
        if story_manager.story != None:
            del story_manager.story
        
        characters = []
        current_character = "You"

        print("\n\n")

        splash_choice = splash()

        if splash_choice == "new":
            print("\n\n")
            context, prompt = select_game()
            console_print(instructions())
            print("\nGenerating story...")

            story_manager.start_new_story(
                prompt, context=context, upload_story=upload_story
            )
            print("\n")
            console_print(str(story_manager.story))

        else:
            load_ID = input("What is the ID of the saved game? ")
            result = story_manager.load_new_story(load_ID)
            print("\nLoading Game...\n")
            print(result)

        while True:
            sys.stdin.flush()
            action = input("> ")
            if action.lower() == "restart":
                rating = input("Please rate the story quality from 1-10: ")
                rating_float = float(rating)
                story_manager.story.rating = rating_float
                break

            elif action.lower() == "quit":
                rating = input("Please rate the story quality from 1-10: ")
                rating_float = float(rating)
                story_manager.story.rating = rating_float
                exit()

            elif action.lower() == "nosaving":
                upload_story = False
                story_manager.story.upload_story = False
                console_print("Saving turned off.")

            elif action.lower() == "help":
                console_print(instructions())

            elif action.lower() == "censor off":
                generator.censor = False

            elif action.lower() == "censor on":
                generator.censor = True

            elif action.lower() == "settemp":
                userinput = input("Enter new temperature (Current value = " + str(generator.temp) + "): ")
                if userinput:
                    generator.temp = float(userinput)

            elif action.lower() == "setmem":
                userinput = input("Enter new memory (Current value = " + str(generator.top_k) + "): ")
                if userinput:
                    generator.top_k = int(userinput)

            elif action.lower() == "save":
                if upload_story:
                    id = story_manager.story.save_to_storage()
                    console_print("Game saved.")
                    console_print(
                        "To load the game, type 'load' and enter the following ID: "
                        + id
                    )
                else:
                    console_print("Saving has been turned off. Cannot save.")

            elif action.lower() == "load":
                load_ID = input("What is the ID of the saved game?")
                result = story_manager.story.load_from_storage(load_ID)
                console_print("\nLoading Game...\n")
                console_print(result)

            elif len(action.split(" ")) == 2 and action.split(" ")[0].lower() == "load":
                load_ID = action.split(" ")[1]
                result = story_manager.story.load_from_storage(load_ID)
                console_print("\nLoading Game...\n")
                console_print(result)

            elif action.lower() == "print":
                print("\nPRINTING\n")
                print(str(story_manager.story))

            elif action.lower() == "revert":

                if len(story_manager.story.actions) is 0:
                    console_print("You can't go back any farther. ")
                    continue

                story_manager.story.actions = story_manager.story.actions[:-1]
                story_manager.story.results = story_manager.story.results[:-1]
                console_print("Last action reverted. ")
                if len(story_manager.story.results) > 0:
                    console_print(story_manager.story.results[-1])
                else:
                    console_print(story_manager.story.story_start)
                continue
                
            elif len(action.split(" ")) >= 2 and action.split(" ")[0] == "setchar":

                new_char = action[len(action.split(" ")[0]):].strip()
                if new_char == "":
                    console_print("Character name cannot be empty")
                    continue
                is_known_char = False
                for known_char in characters:
                    if known_char.lower() == new_char.lower():
                        is_known_char = True
                        new_char = known_char
                        break
                if not is_known_char:
                    characters.append(new_char)
                
                current_character = new_char
                console_print("Switched to character " + new_char)
                continue
                
            elif len(action.split(" ")) == 2 and action.split(" ")[0] == 'infto':

                try:
                    inference_timeout = int(action.split(" ")[1])
                    console_print(f"Set timeout to {inference_timeout}")
                except:
                    console_print("Failed to set timeout. Example usage: infto 30")
                continue

            else:
                if action == "":
                    action = ""
                    try:
                        result = act(action)
                    except FunctionTimedOut:
                        notify_hanged()
                        continue
                    console_print(result)

                elif action[0] == '"':
                    if current_character == "You":
                        action = "You say " + action
                    else:
                        action = current_character + " says " + action
                    
                elif action[0] == '!':
                    action = "\n" + action[1:].replace("\\n", "\n") + "\n"

                else:
                    action = action.strip()
                    action = action[0].lower() + action[1:]

                    action = current_character + " " + action

                    if action[-1] not in [".", "?", "!"]:
                        action = action + "."

                    action = "\n> " + action + "\n"

                try:
                    result = "\n" + act(action)
                except FunctionTimedOut:
                    notify_hanged()
                    continue
                if len(story_manager.story.results) >= 2:
                    similarity = get_similarity(
                        story_manager.story.results[-1], story_manager.story.results[-2]
                    )
                    if similarity > 0.9:
                        story_manager.story.actions = story_manager.story.actions[:-1]
                        story_manager.story.results = story_manager.story.results[:-1]
                        console_print(
                            "Woops that action caused the model to start looping. Try a different action to prevent that."
                        )
                        continue

                if player_won(result):
                    console_print(result + "\n CONGRATS YOU WIN")
                    break
                elif player_died(result):
                    console_print(result)
                    console_print("YOU DIED. GAME OVER")
                    console_print("\nOptions:")
                    console_print("0) Start a new game")
                    console_print(
                        "1) \"I'm not dead yet!\" (If you didn't actually die) "
                    )
                    console_print("Which do you choose? ")
                    choice = get_num_options(2)
                    if choice == 0:
                        break
                    else:
                        console_print("Sorry about that...where were we?")
                        console_print(result)

                else:
                    console_print(result)


if __name__ == "__main__":
    play_aidungeon_2()
