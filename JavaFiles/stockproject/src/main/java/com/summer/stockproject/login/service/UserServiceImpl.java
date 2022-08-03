package com.summer.stockproject.login.service;

import com.summer.stockproject.login.Entity.User;
import com.summer.stockproject.login.dao.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.Optional;

@Service
public class UserServiceImpl implements UserService {

    private UserRepository userRepository;
    private HashService hashService;


    @Autowired
    public UserServiceImpl(UserRepository userRepository, HashService hashService) {
        this.hashService = hashService;
        this.userRepository = userRepository;
    }

    @Override
    public User getReferenceById(String email) {
        return userRepository.getReferenceById(email);
    }

    public boolean doesUserExist(String username) {

        Optional<User> temp = userRepository.findById(username);
        return temp.isPresent();
    }

    public void save(User user) {
        SecureRandom random = new SecureRandom();
        byte[] salt = new byte[16];
        random.nextBytes(salt);
        String encodedSalt = Base64.getEncoder().encodeToString(salt);
        String hashedPassword = hashService.getHashedValue(user.getPassword(), encodedSalt);
        user.setPassword(hashedPassword);
        user.setSaltt(encodedSalt);
        userRepository.save(user);

    }
}
