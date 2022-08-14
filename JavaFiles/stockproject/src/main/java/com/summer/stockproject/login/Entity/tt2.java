package com.summer.stockproject.login.Entity;

import javax.persistence.*;

@Entity
@Table(name = "tt2")
public class tt2 {
    @Id
    @Column(name = "id")
    private int id;

    @ManyToOne(targetEntity = tt1.class)
    @JoinColumn(name="username")
    private String username;
    @Column(name = "hobby")
    private String hobby;

    public tt2() {

    }

    public tt2(int id, String username, String hobby) {
        this.id = id;
        this.username = username;
        this.hobby = hobby;
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getHobby() {
        return hobby;
    }

    public void setHobby(String hobby) {
        this.hobby = hobby;
    }

    @Override
    public String toString() {
        return "tt2{" +
                "id=" + id +
                ", username='" + username + '\'' +
                ", hobby='" + hobby + '\'' +
                '}';
    }
}
