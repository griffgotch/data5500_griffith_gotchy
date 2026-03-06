from Deck_of_cards import *

def score_calc(hand):
    total = sum(card.val for card in hand)
    num_aces = sum(1 for card in hand if card.face == "Ace")
    
    while total > 21 and num_aces > 0:
        total -= 10
        num_aces -= 1
    
    return total

def display_hand(hand, name):
    print(f"\n{name}'s hand:")
    for card in hand:
        print(f"  {card.face} of {card.suit}")
    print(f"{name}'s score: {score_calc(hand)}")

def play_blackjack(deck):
    print("Starting new game...")

    print("\nDeck before shuffle:")
    deck.print_deck()
    
    deck.shuffle_deck()
    
    print("\nDeck after shuffle:")
    deck.print_deck()

    player_hand = [deck.get_card(), deck.get_card()]
    dealer_hand = [deck.get_card(), deck.get_card()]

    print("\n--- YOUR TURN ---")
    display_hand(player_hand, "Player")

    while True:
        player_score = score_calc(player_hand)
        
        if player_score > 21:
            print("\nYou busted! Your score exceeded 21. You lose!")
            return

        choice = input("\nWould you like a hit? (y/n): ").lower()
        
        if choice == 'y':
            new_card = deck.get_card()
            player_hand.append(new_card)
            print(f"\nYou drew: {new_card.face} of {new_card.suit}")
            display_hand(player_hand, "Player")
        elif choice == 'n':
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    print("--- DEALER'S TURN ---")
    display_hand(dealer_hand, "Dealer")

    while score_calc(dealer_hand) < 17:
        print("\nDealer hits...")
        new_card = deck.get_card()
        dealer_hand.append(new_card)
        print(f"Dealer drew: {new_card.face} of {new_card.suit}")
        display_hand(dealer_hand, "Dealer")

    player_score = score_calc(player_hand)
    dealer_score = score_calc(dealer_hand)
    
    print("FINAL RESULTS")
    print(f"Your score: {player_score}")
    print(f"Dealer's score: {dealer_score}")
    print()

    if dealer_score > 21:
        print("Dealer busted! You win!")
    elif player_score > dealer_score:
        print("Your score is higher than the dealer's. You win!")
    elif player_score == dealer_score:
        print("Dealer's score is equal to yours. You lose!")
    else:
        print("Dealer's score is higher than yours. You lose!")


def main():
    print("Welcome to Blackjack!")
    
    
    deck = DeckOfCards()
    
    play_blackjack(deck)
    
    while True:
        play_again = input("\nWould you like to play again? (y/n): ").lower()
        
        if play_again == 'y':
            play_blackjack(deck)
        elif play_again == 'n':
            print("Thanks for playing!")
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


if __name__ == "__main__":
    main()